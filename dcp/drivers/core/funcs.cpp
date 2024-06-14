#include "map"
#include "result.h"
#include "status.hpp"
#include "string"
#include "utils.hpp"
#include <chrono>
#include <cstring>
#include <dlapi.h>
#include <fitsio.h>
#include <thread>
#include <vector>

Result<ExposeResult, const char *>
expose(dl::ICameraPtr camera, dl::ISensorPtr sensor, ExposureInfo exp_info) {
  if (exp_info.bin_x != 1 || exp_info.bin_y != 1) {
    await(camera->queryCapability(dl::ICamera::eSupportsOnChipBinning));
    if (!camera->getCapability(dl::ICamera::eSupportsOnChipBinning)) {
      return Err(
          "Binning requested, but camera does not support on-chip binning! Use "
          "--binx=1 and --biny=1, and perform binning yourself afterward.");
    }
    try {
      await(sensor->setSetting(dl::ISensor::UseOnChipBinning, 1));
    } catch (std::exception &ex) {
      return Err(ex.what());
    }
  }

  if (exp_info.overscan == 1) {
    await(camera->queryCapability(dl::ICamera::eSupportsOverscan));
    if (!camera->getCapability(dl::ICamera::eSupportsOverscan)) {
      return Err("Camera does not support overscan! Use --disable_overscan.");
    }

    try {
      await(sensor->setSetting(dl::ISensor::UseOverscan, 1));
    } catch (std::exception &ex) {
      return Err(ex.what());
    }
  }

  try {
    await(sensor->abortExposure());
  } catch (std::exception &ex) {
    // doesn't matter
  }

  auto sensor_info = get_sensor_info(sensor);
  std::this_thread::sleep_for(std::chrono::milliseconds(50));

  dl::TSubframe subframe;
  subframe.top = 0;
  subframe.left = 0;
  subframe.width = sensor_info.pixels_x / exp_info.bin_x;
  subframe.height = sensor_info.pixels_y / exp_info.bin_y;
  subframe.binX = exp_info.bin_x;
  subframe.binY = exp_info.bin_y;

  dl::TExposureOptions exposure_options;
  exposure_options.duration =
      std::max(exp_info.duration, sensor_info.exposure_duration_min);
  exposure_options.binX = exp_info.bin_x;
  exposure_options.binY = exp_info.bin_y;
  exposure_options.readoutMode = 0; // normal readout mode
  exposure_options.isLightFrame = exp_info.imagetype != ImageType::Dark;
  exposure_options.useRBIPreflash = false;
  exposure_options.useExtTrigger = false;

  try {
    await(sensor->setSubframe(subframe));
  } catch (std::exception &ex) {
    std::cout << "image_is_ready failed" << std::endl;
    return Err(ex.what());
    // return Err("setSubframe failed");
  }

  try {
    // std::cout << "starting actual exposure" << std::endl;
    await(sensor->startExposure(exposure_options));
  } catch (std::exception &ex) {
    std::cout << "startExposure failed" << std::endl;
    return Err(ex.what());
    // return Err("startExposure failed");
  }

  do {
    try {
      if (image_is_ready(camera, sensor))
        break;
    } catch (std::exception &ex) {
      std::cout << "image_is_ready failed" << std::endl;
      return Err(ex.what());
      // return Err("image_is_ready failed");
    }
  } while (true);

  //std::this_thread::sleep_for(std::chrono::milliseconds(20));
  std::this_thread::sleep_for(std::chrono::milliseconds(200));

  // get data
  try {
    await(sensor->startDownload());
  } catch (std::exception &ex) {
    std::cout << "startDownload failed" << std::endl;
    return Err(ex.what());
    // return Err("startDownload failed");
  }

  std::this_thread::sleep_for(std::chrono::milliseconds(20));

  // Sometimes the image download from the sensor can fail without returning an error.
  // This leaves the image variable as a null pointer which can result in a segfault if dereferenced.
  auto image = sensor->getImage();
  if (image == nullptr) {
    return Err("Image download from sensor failed! (getImage failed)");
  }
  //////////  doesn't work //////////////////
  // if (image == nullptr) {
  //   std::cout << "getImage failed, trying getImage process again, sleep 5" << std::endl;
  //   std::this_thread::sleep_for(std::chrono::milliseconds(5000));
  //   try {
  //     std::cout << "done, now startDownload" << std::endl;
  //     await(sensor->startDownload());
  //   } catch (std::exception &ex) {
  //     std::cout << "startDownload failed after trying to getImage"<< std::endl;
  //     return Err(ex.what());
  //     //return Err("startDownload failed after trying to getImage");
  //   }
  //   std::cout << "sleep 2" << std::endl;
  //   std::this_thread::sleep_for(std::chrono::milliseconds(2000));
  //   std::cout << "done, now getImage" << std::endl;
  //   image = sensor->getImage(); //try to get image again

  //   if (image == nullptr) {
  //     // std::cout << "getImage failed, trying getImage one more time" << std::endl;
  //     return Err("Image download from sensor failed! (getImage failed)");
  //   }
  // }

  std::this_thread::sleep_for(std::chrono::milliseconds(50));

  ExposeResult result;
  result.buffer = image->getBufferData();
  result.bufferlen = image->getBufferLength();
  result.metadata = image->getMetadata();
  result.expinfo = exposure_options;

  return Ok(result);
}


Result<ExposeResult, const char *>
redownload(dl::ICameraPtr camera, dl::ISensorPtr sensor, ExposureInfo exp_info) {
  // if (exp_info.bin_x != 1 || exp_info.bin_y != 1) {
  //   await(camera->queryCapability(dl::ICamera::eSupportsOnChipBinning));
  //   if (!camera->getCapability(dl::ICamera::eSupportsOnChipBinning)) {
  //     return Err(
  //         "Binning requested, but camera does not support on-chip binning! Use "
  //         "--binx=1 and --biny=1, and perform binning yourself afterward.");
  //   }
  //   try {
  //     await(sensor->setSetting(dl::ISensor::UseOnChipBinning, 1));
  //   } catch (std::exception &ex) {
  //     return Err(ex.what());
  //   }
  // }

  // if (exp_info.overscan == 1) {
  //   await(camera->queryCapability(dl::ICamera::eSupportsOverscan));
  //   if (!camera->getCapability(dl::ICamera::eSupportsOverscan)) {
  //     return Err("Camera does not support overscan! Use --disable_overscan.");
  //   }

  //   try {
  //     await(sensor->setSetting(dl::ISensor::UseOverscan, 1));
  //   } catch (std::exception &ex) {
  //     return Err(ex.what());
  //   }
  // }

  // try {
  //   await(sensor->abortExposure());
  // } catch (std::exception &ex) {
  //   // doesn't matter
  // }

  auto sensor_info = get_sensor_info(sensor);
  std::this_thread::sleep_for(std::chrono::milliseconds(50));

  dl::TSubframe subframe;
  subframe.top = 0;
  subframe.left = 0;
  subframe.width = sensor_info.pixels_x / exp_info.bin_x;
  subframe.height = sensor_info.pixels_y / exp_info.bin_y;
  subframe.binX = exp_info.bin_x;
  subframe.binY = exp_info.bin_y;

  dl::TExposureOptions exposure_options;
  exposure_options.duration =
      std::max(exp_info.duration, sensor_info.exposure_duration_min);
  exposure_options.binX = exp_info.bin_x;
  exposure_options.binY = exp_info.bin_y;
  exposure_options.readoutMode = 0; // normal readout mode
  exposure_options.isLightFrame = exp_info.imagetype != ImageType::Dark;
  exposure_options.useRBIPreflash = false;
  exposure_options.useExtTrigger = false;

  try {
    await(sensor->setSubframe(subframe));
  } catch (std::exception &ex) {
    return Err(ex.what());
    // return Err("setSubframe failed");
  }

  //std::this_thread::sleep_for(std::chrono::milliseconds(20));
  std::this_thread::sleep_for(std::chrono::milliseconds(2000));

  // get data
  try {
    std::cout << "startDownload" << std::endl;
    await(sensor->startDownload());
  } catch (std::exception &ex) {
    std::cout << "startDownload failed" << std::endl;
    return Err(ex.what());
    // return Err("startDownload failed");
  }

  std::this_thread::sleep_for(std::chrono::milliseconds(200));

  // Sometimes the image download from the sensor can fail without returning an error.
  // This leaves the image variable as a null pointer which can result in a segfault if dereferenced.
  std::cout << "getImage" << std::endl;
  auto image = sensor->getImage();
  if (image == nullptr) {
    std::cout << "getImage failed, return null pointer" << std::endl;
    return Err("Image download from sensor failed! (getImage failed and returned nullptr)");
  }

  std::this_thread::sleep_for(std::chrono::milliseconds(50));

  ExposeResult result;
  result.buffer = image->getBufferData();
  result.bufferlen = image->getBufferLength();
  result.metadata = image->getMetadata();
  result.expinfo = exposure_options;

  return Ok(result);
}

void save_image(ExposeResult expres, std::string serial, const char *filepath, int focus_pos,
                std::map<std::string, std::string> header_map) {

  unsigned short *buffer = expres.buffer;
  unsigned int nelements = expres.bufferlen;
  auto expinfo = expres.expinfo;
  auto metadata = expres.metadata;

  fitsfile *fptr;
  int status = 0;
  long naxes[2] = {metadata.width, metadata.height};
  int bitpix = USHORT_IMG;
  const char *frametype = (expinfo.isLightFrame ? "Light Frame" : "Dark Frame");

  remove(filepath);

  fits_create_file(&fptr, filepath, &status);
  print_fits_err(status);
  fits_create_img(fptr, bitpix, 2, naxes, &status);
  print_fits_err(status);
  fits_write_img(fptr, TUSHORT, 1, nelements, buffer, &status);
  print_fits_err(status);

  fits_write_date(fptr, &status);
  print_fits_err(status);
  fits_update_key_dbl(fptr, "EXPTIME", metadata.exposureDuration, 6,
                      "Total exposure time in seconds", &status);

  // Some cameras do not record their gain values. We do not want
  // the absence of a gain to crash the program.
  try {
    print_fits_err(status);
    int oldstatus = status;
    fits_update_key_dbl(fptr, "EGAIN", metadata.eGain, 6,
                        "Electronic gain in e-/ADU", &status);
    throw(oldstatus);
  }
  catch(int mynum) {
    status = mynum;
  }

  print_fits_err(status);
  fits_update_key_dbl(fptr, "XBINNING", metadata.binX, 2,
                      "Binning factor in width", &status);
  print_fits_err(status);
  fits_update_key_dbl(fptr, "YBINNING", metadata.binY, 2,
                      "Binning factor in height", &status);
  print_fits_err(status);
  fits_update_key_str(fptr, "IMAGETYP", frametype, "Type of image", &status);
  print_fits_err(status);
 
  fits_update_key_dbl(fptr, "CCD-TEMP", expres.coolerinfo.sensor_temp, 6,
                      "Sensor temperature at end of exposure in degrees C",
                      &status);
  print_fits_err(status);
  fits_update_key_dbl(fptr, "HSINKT", expres.coolerinfo.heatsink_temp, 6,
                      "Heatsink temperature at end of exposure in degrees C",
                      &status);
  print_fits_err(status);
  
  fits_update_key_str(fptr, "SERIALNO", serial.c_str(), "Camera serial number",
                      &status);
  print_fits_err(status);

  fits_update_key_lng(fptr, "FOCUSPOS", focus_pos, "Lens focus position (-1 means position not available)",
                      &status);
  print_fits_err(status);

  for (auto const &[key, value] : header_map) {
    fits_update_key_str(fptr, key.c_str(), value.c_str(), "", &status);
    print_fits_err(status);
  }

  fits_close_file(fptr, &status);
  print_fits_err(status);
}
