#pragma once
// Shared between the artwork-fetch lambda and the display lambda
// (both live in the generated main.cpp — single translation unit).
static uint8_t art_buf[32 * 32 * 2];  // RGB565 big-endian, from /artwork-raw
static bool art_have = false;
