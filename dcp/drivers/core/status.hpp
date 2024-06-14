#include <dlapi.h>
#include <tuple>
#include <vector>
#include "utils.hpp"

SensorInfo get_sensor_info(dl::ISensorPtr sensor);
CoolerInfo get_temp_info(dl::ICameraPtr camera, dl::ITECPtr cooler);
float set_temp(dl::ITECPtr cooler, dl::ISensorPtr sensor, float temp);
void disable_cooler(dl::ITECPtr cooler);
std::tuple<std::vector<std::string>, std::vector<dl::ICamera::Model>> enumerate_cameras(dl::IGatewayPtr gateway);
std::ostream& operator<<(std::ostream& os, CoolerInfo info);
