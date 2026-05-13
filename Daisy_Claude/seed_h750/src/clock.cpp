// clock.c — STM32H750 clock tree bring-up
//
// Target topology (see spec 01 §2 and spec 02 §7):
//
//   HSE 16 MHz ──┬──→ PLLM=4 ──→ 4 MHz ──→ PLLN=240 ──→ VCO 960 MHz ──┬─ PLL1P/2 ──→ SYSCLK 480 MHz
//                │                                                      ├─ PLL1Q/5 ──→ 192 MHz (spare)
//                │                                                      └─ PLL1R/2 ──→ 480 MHz (spare)
//                └──→ (left on, also feeds PLL2/PLL3 in later steps)
//
//   SYSCLK 480 MHz ──→ D1CPRE /1 ──→ CPU/AXI 480 MHz
//                                ──→ HPRE /2  ──→ HCLK (AHB1/2/3/4) 240 MHz
//                                            ──→ APB1 /2 → 120 MHz
//                                            ──→ APB2 /2 → 120 MHz
//                                            ──→ APB3 /2 → 120 MHz
//                                            ──→ APB4 /2 → 120 MHz
//
// VOS0 voltage scaling is required for anything above 400 MHz. On H7 rev V
// silicon (which the Daisy Seed Rev 7 uses) reaching VOS0 requires the
// SYSCFG->PWRCR.ODEN ("overdrive enable") kick after enabling VOS1; see
// RM0433 rev 9 §6.6.2 and errata ES0392.
//
// Flash wait states at VOS0 / AXI = 240 MHz: LATENCY = 4, WRHIGHFREQ = 0b10
// (RM0433 rev 9 Table 17 "FLASH recommended number of wait states").
//
// Every wait-for-ready loop spins forever on failure — the intent is that a
// debugger catches the exact step that stalled, rather than having the code
// try to "gracefully degrade" and mask the problem.

#include "stm32h750xx.h"
#include "core_cm7.h"

#include "clock.h"
#include "systick.h"

// Published after the sequence completes so SysTick and drivers can compute
// their own dividers without duplicating the constants.
uint32_t g_sysclk_hz = 0;
uint32_t g_hclk_hz   = 0;

// ---- PLL1 divider values (HSE=16 MHz → 480 MHz SYSCLK) ----
// All values are the *divider*, not the register field. The register fields
// DIVN1/DIVP1/DIVQ1/DIVR1 encode (value - 1); we handle that at the write.
#define PLL1_M  4U     // 16 MHz / 4  = 4 MHz PLL input (VCIRANGE_2)
#define PLL1_N  240U   // 4 MHz * 240 = 960 MHz VCO (VCOWIDE)
#define PLL1_P  2U     // 960 / 2 = 480 MHz → SYSCLK
#define PLL1_Q  5U     // 960 / 5 = 192 MHz → spare (USB/SDMMC later)
#define PLL1_R  2U     // 960 / 2 = 480 MHz → spare

// ---- PLL3 divider values (HSE=16 MHz → ~49.167 MHz for SAI1 kernel) ----
// Target is 12.288 MHz MCLK = 256 × 48 kHz, reached via SAI_MCKDIV = 2
// (which halves the kernel twice → /4). Exact 12.288 MHz from a 16 MHz HSE
// is impossible with integer dividers (12.288 / 16 = 96/125, the factor
// 125 = 5^3 cannot be hit), so we accept ~300 ppm high. Inaudible; locked
// in spec 04 §10 decision #1. A future board with a 12.288 or 24.576 MHz
// MCLK-matched crystal, or PLL3FRACN, could make it exact.
#define PLL3_M  6U     // 16 MHz / 6   = 2.667 MHz PFD (RGE = 2-4 MHz)
#define PLL3_N  295U   // 2.667 * 295  = 786.67 MHz VCO (VCOWIDE)
#define PLL3_P  16U    // 786.67 / 16  = 49.167 MHz → SAI1 kernel

static void spin_until(volatile uint32_t *reg, uint32_t mask, uint32_t want) {
  while ((*reg & mask) != want) {
    // spin; on a real fault a debugger will break here.
  }
}

void configure_clocks(void) {
  // ============================================================
  // 1. Power supply — LDO only (Daisy Seed has no SMPS inductor).
  //    PWR_CR3 is write-once-after-reset, so this runs once.
  //    Set LDOEN=1, SMPSEN=0, BYPASS=0.
  // ============================================================
  PWR->CR3 = (PWR->CR3 & ~(PWR_CR3_SCUEN | PWR_CR3_LDOEN | PWR_CR3_BYPASS))
           | PWR_CR3_LDOEN;
  spin_until(&PWR->CSR1, PWR_CSR1_ACTVOSRDY, PWR_CSR1_ACTVOSRDY);

  // ============================================================
  // 2. Voltage scaling — VOS0 (required for 480 MHz).
  //    On H750 rev V we must first set VOS = 0b11 in PWR_D3CR,
  //    then kick SYSCFG->PWRCR.ODEN so the internal overdrive
  //    actually engages.
  // ============================================================
  // 2a. VOS = 0b11 → VOS1 nominal (highest regular scale)
  PWR->D3CR = (PWR->D3CR & ~PWR_D3CR_VOS) | PWR_D3CR_VOS;
  // small read-back delay per RM0433 §6.6.2 before touching SYSCFG
  (void)PWR->D3CR;

  // 2b. enable SYSCFG clock, then the overdrive bit that unlocks VOS0
  RCC->APB4ENR |= RCC_APB4ENR_SYSCFGEN;
  (void)RCC->APB4ENR;  // ensure the write lands before SYSCFG is touched
  SYSCFG->PWRCR |= SYSCFG_PWRCR_ODEN;

  // 2c. wait for the regulator to report the new scale is live
  spin_until(&PWR->D3CR, PWR_D3CR_VOSRDY, PWR_D3CR_VOSRDY);

  // ============================================================
  // 3. Turn on HSE (16 MHz crystal on the Seed).
  // ============================================================
  RCC->CR |= RCC_CR_HSEON;
  spin_until(&RCC->CR, RCC_CR_HSERDY, RCC_CR_HSERDY);

  // ============================================================
  // 4. Flash wait states BEFORE bumping SYSCLK — per RM0433 Table
  //    17. Writing the latency early is safe because flash at
  //    64 MHz is fine with 4 WS; what matters is that 4 WS is in
  //    place BY THE TIME we switch to 480 MHz.
  // ============================================================
  FLASH->ACR = FLASH_ACR_LATENCY_4WS | FLASH_ACR_WRHIGHFREQ_1;
  spin_until(&FLASH->ACR,
             FLASH_ACR_LATENCY | FLASH_ACR_WRHIGHFREQ,
             FLASH_ACR_LATENCY_4WS | FLASH_ACR_WRHIGHFREQ_1);

  // ============================================================
  // 5. Configure PLL1: source = HSE, M/N/P/Q/R from constants.
  //    Must be done with PLL1 OFF (which it is at reset).
  // ============================================================
  // 5a. PLLCKSELR — PLL source = HSE, DIVM1 = PLL1_M
  RCC->PLLCKSELR = RCC_PLLCKSELR_PLLSRC_HSE
                 | (PLL1_M << RCC_PLLCKSELR_DIVM1_Pos);

  // 5b. PLL1DIVR — dividers are stored as (value - 1)
  RCC->PLL1DIVR = ((PLL1_N - 1U) << RCC_PLL1DIVR_N1_Pos)
                | ((PLL1_P - 1U) << RCC_PLL1DIVR_P1_Pos)
                | ((PLL1_Q - 1U) << RCC_PLL1DIVR_Q1_Pos)
                | ((PLL1_R - 1U) << RCC_PLL1DIVR_R1_Pos);

  // 5c. PLLCFGR — for PLL1:
  //       PLL1VCOSEL = 0 (wide, 192-960 MHz — we're at 960)
  //       PLL1RGE    = 0b10 (4-8 MHz input range for 4 MHz PFD)
  //       DIVP1EN/Q/R = 1 (enable each output divider)
  //       PLL1FRACEN  = 0 (integer mode)
  // We write this field explicitly, preserving PLL2/PLL3 bits which
  // are untouched at reset and will be configured in later steps.
  uint32_t pllcfgr = RCC->PLLCFGR;
  pllcfgr &= ~(RCC_PLLCFGR_PLL1VCOSEL
             | RCC_PLLCFGR_PLL1RGE
             | RCC_PLLCFGR_PLL1FRACEN);
  pllcfgr |= (0x2U << RCC_PLLCFGR_PLL1RGE_Pos)  // VCIRANGE_2
           | RCC_PLLCFGR_DIVP1EN
           | RCC_PLLCFGR_DIVQ1EN
           | RCC_PLLCFGR_DIVR1EN;
  RCC->PLLCFGR = pllcfgr;

  // 5d. Enable PLL1 and wait for lock
  RCC->CR |= RCC_CR_PLL1ON;
  spin_until(&RCC->CR, RCC_CR_PLL1RDY, RCC_CR_PLL1RDY);

  // ============================================================
  // 6. Bus dividers — set BEFORE switching SYSCLK so none of the
  //    APBs briefly run out of spec.
  // ============================================================
  // D1CFGR: D1CPRE=/1, HPRE=/2, D1PPRE=/2 (APB3)
  RCC->D1CFGR = RCC_D1CFGR_D1CPRE_DIV1
              | RCC_D1CFGR_HPRE_DIV2
              | RCC_D1CFGR_D1PPRE_DIV2;
  // D2CFGR: D2PPRE1=/2 (APB1), D2PPRE2=/2 (APB2)
  RCC->D2CFGR = RCC_D2CFGR_D2PPRE1_DIV2 | RCC_D2CFGR_D2PPRE2_DIV2;
  // D3CFGR: D3PPRE=/2 (APB4)
  RCC->D3CFGR = RCC_D3CFGR_D3PPRE_DIV2;

  // ============================================================
  // 7. Switch SYSCLK to PLL1 and confirm the switch landed.
  // ============================================================
  RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_PLL1;
  spin_until(&RCC->CFGR, RCC_CFGR_SWS, RCC_CFGR_SWS_PLL1);

  // ============================================================
  // 8. Publish the results for anyone who needs the frequency.
  // ============================================================
  g_sysclk_hz = SYSCLK_HZ;
  g_hclk_hz   = HCLK_HZ;
}

// ============================================================================
// configure_sai1_clock — PLL3 bring-up for the SAI1 kernel clock.
//
// PLL3 sits on HSE alongside PLL1/PLL2. We use PLL3P only; PLL3Q and PLL3R
// are left disabled. After PLL3 locks we select PLL3P as the SAI1 kernel
// source via RCC_D2CCIP1R.SAI1SEL = 0b010 (RM0433 §8.7.36).
//
// Unlike configure_clocks(), this routine has a BOUNDED wait on the lock
// bit: if PLL3 fails to lock within ~5 ms of SysTick, we return false and
// let main() signal the fault visibly (fast LED blink). PLL1 failure bricks
// the chip by definition; PLL3 failure just loses audio — worth reporting.
// ============================================================================
bool configure_sai1_clock(void) {
  // --- PLL3 must be OFF to reprogram its dividers (RM0433 §8.5.3).
  // It is off at reset, but be explicit in case we're re-entered.
  RCC->CR &= ~RCC_CR_PLL3ON;
  while ((RCC->CR & RCC_CR_PLL3RDY) != 0U) {
    // wait for the PLL to actually stop before touching its config
  }

  // --- PLLCKSELR: set DIVM3. DIVM1 was set by configure_clocks() and
  // is preserved; DIVM2 is still at reset (0).
  uint32_t pllckselr = RCC->PLLCKSELR;
  pllckselr &= ~RCC_PLLCKSELR_DIVM3;
  pllckselr |= (PLL3_M << RCC_PLLCKSELR_DIVM3_Pos);
  RCC->PLLCKSELR = pllckselr;

  // --- PLL3DIVR: N (stored as N-1), P (stored as P-1).
  // Q and R dividers left at reset (don't care — their enables stay off).
  RCC->PLL3DIVR = ((PLL3_N - 1U) << RCC_PLL3DIVR_N3_Pos)
                | ((PLL3_P - 1U) << RCC_PLL3DIVR_P3_Pos);

  // --- PLLCFGR: configure PLL3 input range, VCO range, and enable DIVP3.
  //   PLL3RGE  = 0b01 (2-4 MHz PFD)
  //   PLL3VCOSEL = 0 (wide VCO, 192-960 MHz — we're at 786.67)
  //   PLL3FRACEN = 0 (integer mode)
  //   DIVP3EN  = 1, DIVQ3EN = 0, DIVR3EN = 0
  // PLL1 bits set earlier must be preserved.
  uint32_t pllcfgr = RCC->PLLCFGR;
  pllcfgr &= ~(RCC_PLLCFGR_PLL3VCOSEL
             | RCC_PLLCFGR_PLL3RGE
             | RCC_PLLCFGR_PLL3FRACEN
             | RCC_PLLCFGR_DIVP3EN
             | RCC_PLLCFGR_DIVQ3EN
             | RCC_PLLCFGR_DIVR3EN);
  pllcfgr |= (0x1U << RCC_PLLCFGR_PLL3RGE_Pos)   // 2-4 MHz input range
           | RCC_PLLCFGR_DIVP3EN;
  RCC->PLLCFGR = pllcfgr;

  // --- Enable PLL3 and wait for lock with a bounded timeout.
  RCC->CR |= RCC_CR_PLL3ON;
  const uint32_t start = millis();
  while ((RCC->CR & RCC_CR_PLL3RDY) == 0U) {
    if ((millis() - start) >= 5U) {
      return false;  // lock timeout — main() will show a fault blink
    }
  }

  // --- Select PLL3P as SAI1 kernel clock (SAI1SEL = 0b010, RM0433 §8.7.36).
  uint32_t d2ccip1r = RCC->D2CCIP1R;
  d2ccip1r &= ~RCC_D2CCIP1R_SAI1SEL;
  d2ccip1r |= (0x2U << RCC_D2CCIP1R_SAI1SEL_Pos);
  RCC->D2CCIP1R = d2ccip1r;

  return true;
}
