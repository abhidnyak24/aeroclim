#pragma once
// Copy config.example.h to config.local.h for your board and credentials.
// config.local.h is ignored by Git; the default profile needs no credentials.
#if __has_include("config.local.h")
#include "config.local.h"
#else
#include "config.example.h"
#endif
