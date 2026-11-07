"""NWS heat-index approximation. CDI is a project-specific max(T, HI) proxy."""
import math

def heat_index_c(c, rh):
    t = c * 1.8 + 32
    simple = 0.5 * (t + 61 + (t - 68) * 1.2 + rh * .094)
    hi = (simple + t) / 2
    if hi >= 80:
        hi = (-42.379 + 2.04901523*t + 10.14333127*rh - .22475541*t*rh
              - .00683783*t*t - .05481717*rh*rh + .00122874*t*t*rh
              + .00085282*t*rh*rh - .00000199*t*t*rh*rh)
        if rh < 13 and 80 <= t <= 112:
            hi -= (13-rh)/4 * math.sqrt(max(0, (17-abs(t-95))/17))
        elif rh > 85 and 80 <= t <= 87:
            hi += (rh-85)/10 * (87-t)/5
    return (hi-32)/1.8

def cdi(c, rh):
    return max(c, heat_index_c(c, rh))
