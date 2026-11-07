#include "../firmware/AeroClimNode/core.h"
#include <assert.h>
#include <stdio.h>
int main(){
  PMSParser p;uint8_t b[32]{};b[0]=0x42;b[1]=0x4d;b[3]=28;
  b[11]=10;b[13]=25;b[15]=35;
  unsigned sum=0;for(int i=0;i<30;++i)sum+=b[i];b[30]=sum>>8;b[31]=sum&255;
  for(int i=0;i<31;++i){assert(!p.feed(b[i]));}
  assert(p.feed(b[31]));
  assert(p.pm25==25&&p.pm1==10&&p.pm10==35);
  b[31]^=1;for(auto c:b){p.feed(c);}
  assert(p.good==1&&p.bad>=1);
  b[31]^=1;p.feed(0);p.feed(0x42);for(auto c:b){p.feed(c);}
  assert(p.good==2);
  b[29]=1;sum=0;for(int i=0;i<30;++i)sum+=b[i];b[30]=sum>>8;b[31]=sum&255;
  for(auto c:b){p.feed(c);}
  assert(p.good==2);
  Holt h;for(int i=0;i<10;++i)assert(!h.update(30));
  assert(!h.update(36));assert(h.update(36));
  for(int i=0;i<14;++i){h.update(36);}
  assert(h.run==0&&h.level==36);
  assert(!h.update(NAN));puts("Firmware core tests passed");
}
