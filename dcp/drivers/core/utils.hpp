#pragma once
#include "result.h"
#include <boost/filesystem.hpp>
#include <dlapi.h>
#include <map>

struct SensorInfo {
  unsigned int pixels_x;
  unsigned int pixels_y;
  float pixel_size_x;
  float pixel_size_y;
  float cooler_setpoint_min;
  float cooler_setpoint_max;
  unsigned int bin_x_max;
  unsigned int bin_y_max;
  float exposure_duration_min;
  float exposure_precision;
};

struct CoolerInfo {
  bool cooler_enabled;
  float cooler_power;
  float cooler_setpoint;
  float heatsink_temp;
  dl::ISensor::Status sensor_state;
  float sensor_temp;
};

enum ReadoutMode {
  Low = 0,
  Medium = 1,
  High = 2,
  LowStackPro = 3,
  MediumStackPro = 4,
  HighStackPro = 5,
};

enum ImageType {
  Light,
  Dark,
  Bias,
  Flat,
};

struct ExposureInfo {
  float duration;
  ImageType imagetype;
  enum ReadoutMode readout_mode;
  int bin_x;
  int bin_y;
  int overscan;
};

struct ExposeResult {
  unsigned short *buffer;
  unsigned int bufferlen;
  dl::TImageMetadata metadata;
  dl::TExposureOptions expinfo;
  CoolerInfo coolerinfo;
};

static std::map<int, std::string> CAMERA_MODELS{
    {0, "Aluma and Aluma CCD"},
    {1, "Reserved"},
    {2, "Reserved"},
    {3, "Aluma CMOS"},
    {4, "Starchaser"},
    {5, "STC"},
    {6, "Aluma AC2020"},
    {7, "Starchaser E"},
    {8, "Reserved"}
    // ...
};

void await(dl::IPromisePtr promise);

dl::IGatewayPtr initialize_gateway();
void free_gateway(dl::IGatewayPtr gateway);

Result<dl::ICameraPtr, const char *> initialize_camera(dl::IGatewayPtr gateway,
                                                       int n);
Result<dl::ISensorPtr, const char *> initialize_sensor(dl::ICameraPtr camera);
Result<dl::ITECPtr, const char *> initialize_cooler(dl::ICameraPtr camera);

int count_cameras(dl::IGatewayPtr gateway);

void print_fits_err(int status);

template <typename T> T unwrap_or_fail(Result<T, const char *> res) {
  if (res.isOk()) {
    return res.unwrap();
  }
  throw std::runtime_error(res.unwrapErr());
}

std::string get_serial_number(dl::ICameraPtr camera);
std::string get_readout_modes(dl::ISensorPtr sensor);

int auto_filenum(dl::ICameraPtr camera, boost::filesystem::path path);

bool image_is_ready(dl::ICameraPtr camera, dl::ISensorPtr sensor);
