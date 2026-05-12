// params.h — discovery protocol for remote parameter control via OpenOCD/SWD
//
// The macOS host app reads param_anchor's address from the .map file, then
// walks the tree by following child/next pointers to discover all parameters.
// It writes to ParamNode.value fields directly via OpenOCD memory writes.
//
// All nodes live in DTCMRAM (.bss). DTCMRAM bypasses the Cortex-M7 D-cache,
// so host writes are immediately visible to the CPU without cache invalidation.

#ifndef DAISY_CLAUDE_PARAMS_H
#define DAISY_CLAUDE_PARAMS_H

#include <stdint.h>

#define PARAM_ANCHOR_MAGIC  0xDA151E00U
#define PARAM_NODE_MAGIC    0xDA151E01U

typedef enum {
  NODE_GROUP = 0,   // unordered container
  NODE_ARRAY = 1,   // ordered array; all children have identical structure
  NODE_PARAM = 2,   // leaf — has value/min/max/default
} ParamNodeType;

typedef enum {
  UNIT_NONE = 0,
  UNIT_DB   = 1,   // decibels    — host uses linear slider
  UNIT_HZ   = 2,   // hertz       — host uses logarithmic slider
  UNIT_MS   = 3,   // milliseconds
} ParamUnit;

// Common header for every node (20 bytes on 32-bit ARM).
// child and next are raw pointers; the host reads them as 32-bit addresses.
typedef struct ParamNodeHdr ParamNodeHdr;
struct ParamNodeHdr {
  uint32_t      magic;    // PARAM_NODE_MAGIC
  uint8_t       type;     // ParamNodeType
  uint8_t       unit;     // ParamUnit (NODE_PARAM only)
  uint8_t       _pad[2];
  const char   *name;     // pointer into .rodata (flash)
  ParamNodeHdr *child;    // first child node, NULL = leaf
  ParamNodeHdr *next;     // next sibling, NULL = end of list
};

// Leaf parameter node (36 bytes).
// The host writes to `value`; the audio ISR reads it with volatile semantics.
typedef struct {
  ParamNodeHdr   hdr;
  volatile float value;
  float          min;
  float          max;
  float          default_val;
} ParamNode;

// Container node for GROUP and ARRAY (24 bytes).
// count is the element count for ARRAY; 0 for GROUP.
typedef struct {
  ParamNodeHdr  hdr;
  uint32_t      count;
} ParamGroupNode;

// Fixed anchor — the host finds this symbol's address in the .map file.
// Everything else in the tree is reached by following root's child pointer.
typedef struct {
  uint32_t        magic;    // PARAM_ANCHOR_MAGIC
  uint32_t        version;  // = 1
  ParamGroupNode *root;     // pointer to root ParamGroupNode
  uint32_t        _pad;
} ParamAnchor;

extern ParamAnchor param_anchor;

// Convenience pointers into the tree, populated by params_init().
// Used by eq.c to read current parameter values without tree-walking.
typedef struct {
  ParamNode *shelf_gain;   // hi-shelf gain in dB
  ParamNode *shelf_fc;     // hi-shelf corner frequency in Hz
  ParamNode *lp_fc;        // 1-pole LP cutoff in Hz
} EqParamPtrs;

extern EqParamPtrs eq_params[2];  // [0]=left, [1]=right

// Build and wire the static parameter tree. Call before eq_init().
void params_init(void);

#endif // DAISY_CLAUDE_PARAMS_H
