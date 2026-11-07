#pragma once
#include <stdint.h>
#include <math.h>
#include <string.h>
struct Holt {
  unsigned n=0, run=0;
  float level=0,trend=0,sigma=.6f;
  bool update(float x) {
    if (!isfinite(x)) return false;
    if (++n==1) {level=x;return false;}
    float pred=level+trend, resid=x-pred;
    bool spike=n>6 && resid>3*fmaxf(sigma,.4f);
    run=spike?run+1:0;
    if (run>=16) {level=x;trend=0;run=0;return false;}
    if (spike) level=pred;
    else {float next=.5f*x+.5f*pred; trend=.15f*(next-level)+.85f*trend;
      level=next; sigma=.9f*sigma+.125f*fabsf(resid);}
    return run>=2;
  }
};
// Sliding resynchronization: rejects bad headers, lengths, checksum and sensor error.
// PMS5003 standard 32-byte frames only. Variant protocols deliberately unsupported.
struct PMSParser {
  uint8_t b[32]{};
  unsigned used=0;
  uint32_t good=0,bad=0;
  uint16_t pm1=0,pm25=0,pm10=0;
  static uint16_t word(const uint8_t* p){return (uint16_t(p[0])<<8)|p[1];}
  bool feed(uint8_t c){
    if (used==32){memmove(b,b+1,31);used=31;}
    b[used++]=c;
    while (used && (b[0]!=0x42 || (used>1 && b[1]!=0x4d))) {
      memmove(b,b+1,--used);
    }
    if (used>=4 && word(b+2)!=28){++bad;memmove(b,b+1,--used);return false;}
    if (used<32) return false;
    uint16_t sum=0;for(unsigned i=0;i<30;++i) sum+=b[i];
    if(sum!=word(b+30)||b[29]!=0){++bad;memmove(b,b+1,31);used=31;return false;}
    pm1=word(b+10);pm25=word(b+12);pm10=word(b+14);++good;used=0;return true;
  }
};
