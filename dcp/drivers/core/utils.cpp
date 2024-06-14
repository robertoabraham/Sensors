#include <dlapi.h>
#include <fitsio.h>
#include <boost/filesystem.hpp>
#include "result.h"
#include "utils.hpp"

void await(dl::IPromisePtr promise) {
  promise->wait();
  promise->release();
}


int count_cameras(dl::IGatewayPtr gateway) {
  gateway->queryUSBCameras();
  auto count = gateway->getUSBCameraCount();
  return count;
}

Result<dl::ICameraPtr, const char *> initialize_camera(dl::IGatewayPtr gateway, int n) {

	auto count = count_cameras(gateway);

	if (count == 0) {
		return Err("No cameras found!");
	}

  // e.g. query for camera 1 (second camera), but there is only 1 camera (count = 1)
  if (n - 1 > count) {
    return Err("There aren't that many cameras available!");
  } 

	auto camera = gateway->getUSBCamera(n);
	if (!camera) {
		return Err("Could not get camera!");	
	}

	camera->initialize();

  return Ok(camera);
}


dl::IGatewayPtr initialize_gateway() {
  return dl::getGateway();
}

void free_gateway(dl::IGatewayPtr gateway) {
  dl::deleteGateway(gateway);
}


Result<dl::ISensorPtr, const char *> initialize_sensor(dl::ICameraPtr camera) {
  auto sensor = camera->getSensor(0);
  if (!sensor) {
    return Err("Could not initialize sensor!");
  }
  /* sensor->abortExposure()->release(); */
  return Ok(sensor);
}

Result<dl::ITECPtr, const char *> initialize_cooler(dl::ICameraPtr camera) {
  auto cooler = camera->getTEC();
  if (!cooler) {
    return Err("Could not initialize cooler!");
  }
  return Ok(cooler);
}

void print_fits_err(int status) {
  if (status) {
     fits_report_error(stderr, status); /* print error report */
     exit( status );    /* terminate the program, returning error status */
  }
}

std::string get_serial_number(dl::ICameraPtr camera) {
  char buffer[512] = {0};
  size_t lng = 512;
  camera->getSerial(&(buffer[0]), lng);
  return std::string(&(buffer[0]));
}

std::string get_readout_modes(dl::ISensorPtr sensor)
{
  char buf[1028];
  size_t lng = 1028;
  sensor->getReadoutModes(&(buf[0]), lng);
  return std::string(&(buf[0]), lng);
}

int auto_filenum(dl::ICameraPtr camera, boost::filesystem::path path) {
  int counter = 0;
  auto serial = get_serial_number(camera);

  /* auto path = boost::filesystem::initial_path(); */
  for (const auto & file: boost::filesystem::directory_iterator(path)) {
    if (file.path().filename().string().rfind(serial, 0) == 0) { 
      counter += 1;
    }
  }

  return counter;
}

bool image_is_ready(dl::ICameraPtr camera, dl::ISensorPtr sensor) {
  await(camera->queryStatus());
  auto status = camera->getStatus();
  auto sensor_id = sensor->getSensorId();
  auto sensor_status = (sensor_id != 0) ? status.extSensorState : status.mainSensorState;
  return sensor_status == dl::ISensor::ReadyToDownload;
}
