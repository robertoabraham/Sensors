#pragma once
#include "map"
#include "result.h"
#include "string"
#include "utils.hpp"
#include <dlapi.h>

Result<ExposeResult, const char *>
expose(dl::ICameraPtr camera, dl::ISensorPtr sensor, ExposureInfo exp_info);
Result<ExposeResult, const char *>
redownload(dl::ICameraPtr camera, dl::ISensorPtr sensor, ExposureInfo exp_info);
void save_image(ExposeResult expres, std::string serial, const char *filepath, int focus_pos,
                std::map<std::string, std::string> header_map);
