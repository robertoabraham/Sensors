#include "utils.hpp"
#include <dlapi.h>
#include <iostream>
#include <tuple>
#include <vector>

SensorInfo get_sensor_info(dl::ISensorPtr sensor) {
  await(sensor->queryInfo());
  auto info = sensor->getInfo();

  SensorInfo sensor_info;

  sensor_info.pixels_x = info.pixelsX;
  sensor_info.pixels_y = info.pixelsY;
  sensor_info.pixel_size_x = info.pixelSizeX;
  sensor_info.pixel_size_y = info.pixelSizeY;
  sensor_info.cooler_setpoint_min = info.minCoolerSetpoint;
  sensor_info.cooler_setpoint_max = info.maxCoolerSetpoint;
  sensor_info.bin_x_max = info.maxBinX;
  sensor_info.bin_y_max = info.maxBinY;
  sensor_info.exposure_duration_min = info.minExposureDuration;
  sensor_info.exposure_precision = info.exposurePrecision;

  return sensor_info;
}

CoolerInfo get_temp_info(dl::ICameraPtr camera, dl::ITECPtr cooler) {
  await(camera->queryStatus());
  auto status = camera->getStatus();

  CoolerInfo cooler_info;
  cooler_info.cooler_enabled = cooler->getEnabled();
  cooler_info.cooler_setpoint = cooler->getSetpoint();
  cooler_info.cooler_power = status.coolerPower;
  cooler_info.heatsink_temp = status.heatSinkTemperature;
  cooler_info.sensor_temp = status.sensorTemperature;
  return cooler_info;
}

float set_temp(dl::ITECPtr cooler, dl::ISensorPtr sensor, float temp) {
  auto sensor_info = get_sensor_info(sensor);
  auto maxtemp = sensor_info.cooler_setpoint_max;
  auto mintemp = sensor_info.cooler_setpoint_min;

  // clamp
  if (temp > maxtemp) {
    await(cooler->setState(true, maxtemp));
    return maxtemp;
  } else if (temp < mintemp) {
    await(cooler->setState(true, mintemp));
    return mintemp;
  } else {
    await(cooler->setState(true, temp));
    return temp;
  }
}

void disable_cooler(dl::ITECPtr cooler) { await(cooler->setState(false, 20)); }

std::tuple<std::vector<std::string>, std::vector<int>>
enumerate_cameras(dl::IGatewayPtr gateway) {
  auto count = count_cameras(gateway);
  std::vector<std::string> serials(count);
  std::vector<int> models(count);
  for (int i = 0; i < count; ++i) {
    auto cam = unwrap_or_fail(initialize_camera(gateway, i));
    await(cam->queryInfo());
    auto info = cam->getInfo();
    models[i] = info.model;
    serials[i] = get_serial_number(cam);
  }
  return make_tuple(serials, models);
}

std::ostream &operator<<(std::ostream &os, CoolerInfo info) {
  /* os << "Cooler enabled: " << info.cooler_enabled << std::endl; */
  /* os << "Cooler setpoint temperature: " << info.cooler_setpoint << "C" */
  /*    << std::endl; */
  os << "Cooler power draw: " << info.cooler_power << "%" << std::endl;
  os << "Sensor temperature: " << info.sensor_temp << "C" << std::endl;
  os << "Heatsink temperature: " << info.heatsink_temp << "C" << std::endl;
  return os;
}
