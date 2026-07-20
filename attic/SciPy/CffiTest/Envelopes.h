
typedef struct {
  float AttCf;
  float RelCf;
  float PrevOut;
} D_AttRel;

void AttRelProc(D_AttRel* s, float newSamp);

