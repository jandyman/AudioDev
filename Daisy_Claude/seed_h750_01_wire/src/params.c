// params.c — static EQ parameter tree
//
// All nodes are file-static globals in DTCMRAM (.bss).
// params_init() fills in magic/type/name fields and wires child/next pointers.
// Tree structure:
//
//   root (GROUP)
//   └── eq (ARRAY, count=2)
//       ├── [0] left (GROUP)
//       │   ├── hi_shelf (GROUP)
//       │   │   ├── gain  (PARAM, DB,  -24..+24, default 0)
//       │   │   └── fc    (PARAM, HZ,  1k..20k,  default 8k)
//       │   └── lp (GROUP)
//       │       └── fc    (PARAM, HZ,  20..20k,  default 20k)
//       └── [1] right (GROUP)
//           └── (same structure as left)

#include <stddef.h>
#include "params.h"

// ---- Leaf params ----
static ParamNode eq_left_shelf_gain;
static ParamNode eq_left_shelf_fc;
static ParamNode eq_left_lp_fc;
static ParamNode eq_right_shelf_gain;
static ParamNode eq_right_shelf_fc;
static ParamNode eq_right_lp_fc;

// ---- Container groups ----
static ParamGroupNode eq_left_shelf;
static ParamGroupNode eq_left_lp;
static ParamGroupNode eq_left;
static ParamGroupNode eq_right_shelf;
static ParamGroupNode eq_right_lp;
static ParamGroupNode eq_right;
static ParamGroupNode eq_array;
static ParamGroupNode eq_root;

// ---- Public globals ----
ParamAnchor  param_anchor;
EqParamPtrs  eq_params[2];

static void init_param(ParamNode *p, const char *name, ParamUnit unit,
                       float default_val, float min, float max)
{
    p->hdr.magic  = PARAM_NODE_MAGIC;
    p->hdr.type   = (uint8_t)NODE_PARAM;
    p->hdr.unit   = (uint8_t)unit;
    p->hdr.name   = name;
    p->hdr.child  = NULL;
    p->hdr.next   = NULL;
    p->value      = default_val;
    p->min        = min;
    p->max        = max;
    p->default_val = default_val;
}

static void init_group(ParamGroupNode *g, const char *name,
                       ParamNodeType type, uint32_t count)
{
    g->hdr.magic = PARAM_NODE_MAGIC;
    g->hdr.type  = (uint8_t)type;
    g->hdr.unit  = (uint8_t)UNIT_NONE;
    g->hdr.name  = name;
    g->hdr.child = NULL;
    g->hdr.next  = NULL;
    g->count     = count;
}

void params_init(void)
{
    // ---- Leaf params ----
    init_param(&eq_left_shelf_gain,  "gain", UNIT_DB,  0.0f,     -24.0f,  24.0f);
    init_param(&eq_left_shelf_fc,    "fc",   UNIT_HZ,  8000.0f, 1000.0f, 20000.0f);
    init_param(&eq_left_lp_fc,       "fc",   UNIT_HZ, 20000.0f,   20.0f, 20000.0f);
    init_param(&eq_right_shelf_gain, "gain", UNIT_DB,  0.0f,     -24.0f,  24.0f);
    init_param(&eq_right_shelf_fc,   "fc",   UNIT_HZ,  8000.0f, 1000.0f, 20000.0f);
    init_param(&eq_right_lp_fc,      "fc",   UNIT_HZ, 20000.0f,   20.0f, 20000.0f);

    // ---- Container groups ----
    init_group(&eq_left_shelf,  "hi_shelf", NODE_GROUP, 0U);
    init_group(&eq_left_lp,     "lp",       NODE_GROUP, 0U);
    init_group(&eq_left,        "left",     NODE_GROUP, 0U);
    init_group(&eq_right_shelf, "hi_shelf", NODE_GROUP, 0U);
    init_group(&eq_right_lp,    "lp",       NODE_GROUP, 0U);
    init_group(&eq_right,       "right",    NODE_GROUP, 0U);
    init_group(&eq_array,       "eq",       NODE_ARRAY, 2U);
    init_group(&eq_root,        "root",     NODE_GROUP, 0U);

    // ---- Wire child/next pointers ----
    eq_left_shelf.hdr.child      = &eq_left_shelf_gain.hdr;
    eq_left_shelf_gain.hdr.next  = &eq_left_shelf_fc.hdr;

    eq_left_lp.hdr.child         = &eq_left_lp_fc.hdr;

    eq_left.hdr.child            = &eq_left_shelf.hdr;
    eq_left_shelf.hdr.next       = &eq_left_lp.hdr;

    eq_right_shelf.hdr.child     = &eq_right_shelf_gain.hdr;
    eq_right_shelf_gain.hdr.next = &eq_right_shelf_fc.hdr;

    eq_right_lp.hdr.child        = &eq_right_lp_fc.hdr;

    eq_right.hdr.child           = &eq_right_shelf.hdr;
    eq_right_shelf.hdr.next      = &eq_right_lp.hdr;

    eq_array.hdr.child           = &eq_left.hdr;
    eq_left.hdr.next             = &eq_right.hdr;

    eq_root.hdr.child            = &eq_array.hdr;

    // ---- Anchor ----
    param_anchor.magic   = PARAM_ANCHOR_MAGIC;
    param_anchor.version = 1U;
    param_anchor.root    = &eq_root;
    param_anchor._pad    = 0U;

    // ---- Fast-access pointers for eq.c ----
    eq_params[0].shelf_gain = &eq_left_shelf_gain;
    eq_params[0].shelf_fc   = &eq_left_shelf_fc;
    eq_params[0].lp_fc      = &eq_left_lp_fc;
    eq_params[1].shelf_gain = &eq_right_shelf_gain;
    eq_params[1].shelf_fc   = &eq_right_shelf_fc;
    eq_params[1].lp_fc      = &eq_right_lp_fc;
}
