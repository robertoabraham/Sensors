#include "CLI11.hpp"
#include "funcs.hpp"
#include "map"
#include "status.hpp"
#include "utils.hpp"
#include <boost/filesystem.hpp>
#include <fmt/format.h>
#include <iostream>
#include <thread>

int main(int argc, char **argv) {

  CLI::App app{"Dragonfly Narrowband core functions"};

  app.require_subcommand(1);

  // ---------------

  auto sub_cool = app.add_subcommand(
      "cool", "Functions related to cooling and temperatures.");
  sub_cool->require_subcommand(1);

  sub_cool->add_subcommand("disable", "Turns off cooling.");
  sub_cool->add_subcommand(
      "get", "Get the current temperatures for various parts of the system.");

  auto sub_cool_set = sub_cool->add_subcommand(
      "set", "Enables cooling and sets the target cooling temperature.");

  float target_temp;
  sub_cool_set
      ->add_option("temp", target_temp, "Target temperature in degrees C.")
      ->required()
      ->take_first();

  // ----------------

  auto sub_expose = app.add_subcommand("expose", "Take an exposure.");

  int camera_n = -1;
  auto flag_camera =
      sub_expose->add_option("--camera", camera_n,
                             "Which camera to control (see `dfcore list`). "
                             "Defaults to the first non-Starchaser camera.");

  float duration;
  sub_expose
      ->add_option("--duration", duration, "Duration of exposure in seconds.")
      ->required();

  std::string filepath;
  sub_expose->add_option("--savedir", filepath,
                         "Directory to save exposure to. Defaults to the "
                         "current directory where the program is run.");

  std::string filename;
  sub_expose->add_option(
      "--filename", filename,
      "Filename to save exposure to. If not passed, automatically determines "
      "the filename based on number of images in the save directory, the file "
      "type, and the serial number of the camera.");

  bool dark{false};
  auto flag_dark = sub_expose->add_flag("--dark", dark, "Take a dark frame.");

  bool bias{false};
  auto flag_bias = sub_expose
                       ->add_flag("--bias", bias,
                                  "Take a bias frame (shortest possible "
                                  "exposure). Overrides --duration.")
                       ->excludes(flag_dark);

  bool flat{false};
  sub_expose
      ->add_flag("--flat", flat,
                 "Take a flat frame. This is the same as a light frame except "
                 "for file naming and the header values.")
      ->excludes(flag_dark)
      ->excludes(flag_bias);

  bool guider{false};
  sub_expose
      ->add_flag("--guider", guider,
                 "Take an exposure with the off-axis guider.")
      ->excludes(flag_camera);

  int bin_x = 1;
  sub_expose->add_option("--binx", bin_x,
                         "Amount of binning for the x axis. Defaults to 1.");

  int bin_y = 1;
  sub_expose->add_option("--biny", bin_y,
                         "Amount of binning for the y axis. Defaults to 1.");

  int n_exposures = 1;
  sub_expose->add_option(
      "--n", n_exposures,
      "Number of exposures to take with current settings. Defaults to 1.");

  bool disable_overscan{false};
  sub_expose->add_option("--disable_overscan", disable_overscan,
                         "Disable overscan.");

  bool repeatdownload{false};
  sub_expose->add_option("--downloadlastimage", repeatdownload,
                         "CAREFUL! Redownloads last image taken instead of taking a new exposure.");

  bool verbose{false};
  sub_expose->add_flag("--verbose", verbose, "Print verbose output to stdout.");

  std::map<std::string, std::string> header_map;
  auto header_option =
      sub_expose
          ->add_option(
              "--header",
              [&header_map](CLI::results_t
                                vals) { // results_t is just a vector of strings
                for (size_t i = 0; i < vals.size() / 2;
                     i++) // will always be a multiple of 2
                  header_map[vals.at(i * 2)] = vals.at(i * 2 + 1);
                return true;
              },
              "key & value")
          ->type_name("KEY VALUE")
          ->type_size(-2);

  int num_retries_if_exposure_failed = 0;
  sub_expose->add_option(
      "--num_retries_for_failed_exposure", num_retries_if_exposure_failed,
      "Number of retry attempts if an exposure fails. Defaults to 0.");

  int num_download_retries_if_exposure_failed = 2;
  sub_expose->add_option(
      "--num_download_retries_for_failed_exposure", num_download_retries_if_exposure_failed,
      "Number of download retry attempts if an exposure fails, no new exposure taken, simply redownloading the last one taken. Defaults to 2.");

  int focus_pos = -1;
  sub_expose->add_option(
      "--focus_pos", focus_pos,
      "Current focus position (will be written to FITS file). Defaults to -1.");

  // ------------------

  app.add_subcommand("list", "List camera serial numbers and models.");

  // ------------------

  CLI11_PARSE(app, argc, argv);

  // ------------------

  auto gateway = initialize_gateway();
  auto camera_details = enumerate_cameras(gateway);
  auto serials = std::get<0>(camera_details);
  auto models = std::get<1>(camera_details);

  if (serials.size() <= 1) {
    printf("No cameras found!\n");
    return(1);
  }

  if (app.got_subcommand("list")) {
    for (int i = 0; i < serials.size(); ++i) {
      std::cout << "Camera " << i << " --- Serial: " << serials[i]
                << " --- Model: " << CAMERA_MODELS[models[i]] << std::endl;
    }
  } else {

    if (guider) {
      for (int i = 0; i < serials.size(); ++i) {
        if (models[i] == 4 || models[i] == 7) {
          camera_n = i;
          break;
        }
      }
    } else if (camera_n == -1) {
      for (int i = 0; i < serials.size(); ++i) {
        if (models[i] != 4 && models[i] != 7) {
          camera_n = i;
          break;
        }
      }
    }

    auto camera = unwrap_or_fail(initialize_camera(gateway, camera_n));
    auto cooler = unwrap_or_fail(initialize_cooler(camera));

    if (app.got_subcommand("cool")) {

      if (sub_cool->got_subcommand("disable")) {
        disable_cooler(cooler);
        /* Debug("Disabling cooler."); */
      } else if (sub_cool->got_subcommand("get")) {
        std::cout << get_temp_info(camera, cooler) << std::endl;
      } else if (sub_cool->got_subcommand("set")) {
        auto sensor = unwrap_or_fail(initialize_sensor(camera));
        float tgt = set_temp(cooler, sensor, target_temp);
        /* Debug("Setting temperature to " << tgt << " degrees C."); */
      }
    }

    
    if (app.got_subcommand("expose")) {
      auto sensor = unwrap_or_fail(initialize_sensor(camera));

      ExposureInfo expinfo;
      expinfo.bin_x = bin_x;
      expinfo.bin_y = bin_y;
      expinfo.duration = (bias) ? 0. : duration;
      if (dark) {
        expinfo.imagetype = ImageType::Dark;
      } else if (flat) {
        expinfo.imagetype = ImageType::Flat;
      } else if (bias) {
        expinfo.imagetype = ImageType::Bias;
      } else {
        expinfo.imagetype = ImageType::Light;
      }
      expinfo.readout_mode = ReadoutMode::Medium;
      expinfo.overscan = !disable_overscan;

      for (int i = 0; i < n_exposures; ++i) {
        if (filepath.empty()) {
          filepath = boost::filesystem::current_path().string();
        }
        auto serial = get_serial_number(camera);
        auto filenum = auto_filenum(camera, filepath);

        std::string temp_filename;

        if (filename.empty()) {
          temp_filename =
              fmt::format("{}_{}_{}.fits", serial, filenum,
                          (expinfo.imagetype == ImageType::Light)  ? "light"
                          : (expinfo.imagetype == ImageType::Flat) ? "flat"
                          : (expinfo.imagetype == ImageType::Dark) ? "dark"
                                                                   : "bias");
        } else {
          temp_filename = filename;
        }

        auto fullpath = fmt::format("{}/{}", filepath, temp_filename);

        if (verbose) {
          std::cout << "Exposure/redownload in progress" << std::endl;
        }
        
        ExposeResult im;
        if (repeatdownload){
          std::cout << "Redownload in progress" << std::endl;
          im = unwrap_or_fail(redownload(camera, sensor, expinfo));
        }else{
          if (verbose) {
            std::cout << "Exposure in progress" << std::endl;
          }
          im = unwrap_or_fail(expose(camera, sensor, expinfo));
        }
        
        // try {
        //   im = unwrap_or_fail(expose(camera, sensor, expinfo));
        //   // break;
        // }
        // catch (std::runtime_error &err) {
        //   std::cout << "Exposure failed" << std::endl;
        //   for (int i = 1; i <= num_download_retries_if_exposure_failed ; i++) {
        //     try {
        //       std::cout << "Download retry attempt " << i << " of " << num_download_retries_if_exposure_failed << std::endl;
        //       std::this_thread::sleep_for(std::chrono::milliseconds(500));
        //       // std::cout << "free_gateway" << std::endl;
        //       // free_gateway(gateway);
        //       // std::this_thread::sleep_for(std::chrono::milliseconds(500));
        //       // std::cout << "initialize_gateway" << std::endl;
        //       // gateway = initialize_gateway();
        //       // std::cout << "enumerate_cameras(gateway)" << std::endl;
        //       // camera_details = enumerate_cameras(gateway);
        //       // serials = std::get<0>(camera_details);
        //       // models = std::get<1>(camera_details);
        //       std::cout << "initialize camera" << std::endl;
        //       camera = unwrap_or_fail(initialize_camera(gateway, camera_n));
        //       std::cout << "initialize cooler" << std::endl;
        //       cooler = unwrap_or_fail(initialize_cooler(camera));
        //       std::cout << "initialize sensor" << std::endl;
        //       sensor = unwrap_or_fail(initialize_sensor(camera));
        //       std::cout << "redownload" << std::endl;
        //       im = unwrap_or_fail(redownload(camera, sensor, expinfo));
        //       break;
        //     }
        //     catch (std::runtime_error &err) {
        //       if (i < num_download_retries_if_exposure_failed) {
        //         std::cout << "Download retry attempt " << i << " of " << num_download_retries_if_exposure_failed << " failed" << std::endl;
        //       }
        //       else {
        //         free_gateway(gateway);
        //         //throw std::runtime_error("Quitting because of repeated failed exposures.");
        //         throw std::runtime_error("Quiting because repeated downloads failed");
        //       }
        //     }
        //   }
        // }

        // for (int i = 0; i < num_retries_if_exposure_failed + 1; i++) {
        //   try {
        //     im = unwrap_or_fail(expose(camera, sensor, expinfo));
        //     break;
        //   }
        //   catch (std::runtime_error &err) {
        //     std::cout << "Exposure failed" << std::endl;
        //     if (i + 1 <= num_retries_if_exposure_failed) {
        //       std::cout << "Retry attempt " << i + 1 << " of " << num_retries_if_exposure_failed << std::endl;
        //     }
        //     else {
        //       //throw std::runtime_error("Quitting because of repeated failed exposures.");
        //       throw std::runtime_error()
        //     }
        //   }
        // }
        
        im.coolerinfo = get_temp_info(camera, cooler);
        if (verbose) {
          std::cout << "Exposure/Redownload complete" << std::endl;
          std::cout << "Saving image." << std::endl;
        }
        std::cout << fullpath << std::endl;
        save_image(im, serial, fullpath.c_str(), focus_pos, header_map);
        if (verbose) {
          std::cout << "Image saved." << std::endl;
        }
      }
    }
  }

  free_gateway(gateway);
}
