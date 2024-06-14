#include <dlapi.h>

#include <exception>
#include <iostream>
#include <memory>
#include <string>
#include <valarray>
#include <thread>

using namespace dl;

// void await(dl::IPromisePtr promise) {
//   promise->wait();
//   promise->release();
// }

void handlePromise(IPromisePtr pPromise)
{
	auto result = pPromise->wait();
	if (result != IPromise::Complete)
	{
		std::cout << "promise not complete" << std::endl;
		char buf[512] = {0};
		size_t blng = 512;
		pPromise->getLastError(&(buf[0]), blng);
		pPromise->release();
		throw std::logic_error(std::string(&(buf[0]), blng));
	}
	pPromise->release();
}

bool isXferComplete(IPromise *pPromise){
	//Get the status of the promise
	auto status = pPromise->getStatus();
	if (status == IPromise::Complete){
		//image is ready for retrieval
		pPromise->release();
		return true;
	}
	else if (status == IPromise::Error){
		// error occured, report it to user
		char buf[512] = {0};
		size_t blng = 512;
		pPromise->getLastError(&(buf[0]), blng);
		pPromise->release();
		throw std::logic_error(&(buf[0]));
	}
	//otherwise wait
	return false;
}

std::string get_serial_number(ICameraPtr camera) {
  char buffer[512] = {0};
  size_t lng = 512;
  camera->getSerial(&(buffer[0]), lng);
  return std::string(&(buffer[0]));
}

std::string getSerial(ICameraPtr pCamera)
{
	char buf[512] = {0};
	size_t blng = 512;
	pCamera->getSerial(&(buf[0]), blng);
	return std::string(&(buf[0]), blng);
}

int main()
{
	auto pGateway = getGateway();
	auto pDebugCtrl = dynamic_cast<IDebugControl*>(pGateway);
	if (pDebugCtrl){
		pDebugCtrl-> setDebugSetting(IDebugControl::Enable, 4);
	}
	// std::cout << "got gateway" << std::endl;
	pGateway->queryUSBCameras();
	// std::cout << "query usb cameras" << std::endl;
	auto count = pGateway->getUSBCameraCount();
	// std::cout << "count " << count << std::endl;
	
	if (count == 0) 
	{
		std::cout << "Failed to retrieve any USB cameras" << std::endl;
		return 1;
	}

	auto pCamera = pGateway->getUSBCamera(0);
	pCamera->initialize();
	// std::cout << "got gateway of camera 0" << std::endl;
	auto serial  = getSerial(pCamera);
	// auto serial  = get_serial_number(pCamera);
	// std::cout << "got serial" << std::endl;
	std::cout << "Serial: " << serial << std::endl;

	auto pSensor = pCamera->getSensor(0);
	// std::cout << "got sensor" << std::endl;
	
	try
	{
		handlePromise(pSensor->abortExposure());
	}
	catch (std::exception &ex)
	{
		std::cout << "failed abort exposure" << std::endl;
		// We don't care.
	}

	// Set the subframe for a full frame exposure
	auto info    = pSensor->getInfo();
	// std::cout << "got sensor info" << std::endl;
	TSubframe subf;
	subf.top    = 0;
	subf.left   = 0;
	subf.width  = info.pixelsX;
	subf.height = info.pixelsY;
	subf.binX   = 1;
	subf.binY   = 1;

	try
	{
		// std::cout << "setting subframe" << std::endl;
		handlePromise(pSensor->setSubframe(subf));
		// std::cout << "set subframe" << std::endl;
	}
	catch (std::exception &ex)
	{
		std::cout << "Failed to set subframe: " << ex.what() << std::endl;
		deleteGateway(pGateway);
		return 1;
	}

	// Start the exposure
	TExposureOptions options;
	options.duration = 10.;
	options.binX = 1;
	options.binY = 1;
	options.readoutMode = 0;
	options.isLightFrame = false;
	options.useRBIPreflash = false;
	options.useExtTrigger = false;

	try
	{
		handlePromise(pSensor->startExposure(options));
		std::cout << "Started exposure" << std::endl;
	}
	catch (std::exception &ex)
	{
		std::cout << "Failed to start exposure: " << ex.what() << std::endl;
		deleteGateway(pGateway);
		return 1;
	}

	// Wait for exposure to complete
	do
	{
		try
		{
			handlePromise(pCamera->queryStatus());	
		}
		catch (std::exception &ex)
		{
			std::cout << "Failed to query camera status: " << std::endl;
			deleteGateway(pGateway);
			return 1;
		}

		auto status = pCamera->getStatus();
		if (status.mainSensorState == ISensor::ReadyToDownload) break;
	} while (true);
	
	try
	{
		// handlePromise(pSensor->startDownload());
		IPromisePtr pImgPromise = pSensor->startDownload();
		for(int i=0; (i<10)&(!isXferComplete(pImgPromise)); i++){
			std::this_thread::sleep_for(std::chrono::milliseconds(2000));
			std::cout << "Waiting on transfer promise: " << std::endl;
		}
	}
	catch (std::exception &ex) 
	{
		std::cout << "Failed to download the image: " << ex.what() << std::endl;
		deleteGateway(pGateway);
		return 1;
	}

	auto pImg = pSensor->getImage();

	unsigned short * pBuffer = pImg->getBufferData();
	double avg = 0;
	size_t pix = pImg->getBufferLength();	
	
	if (pix == 0) 
	{
		std::cout << "Image buffer is empty" << std::endl;
		deleteGateway(pGateway);
		return 1;
	}

	for (size_t i = 0; i < pix; i++)
	{
		avg += pBuffer[i];
	}
	avg *= 1./pix;

	std::cout << "Image Average: " << avg << " ADU" << std::endl;

	deleteGateway(pGateway);
	return 0;
}
