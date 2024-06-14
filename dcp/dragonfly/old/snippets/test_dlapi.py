import cppyy
import cppyy.ll
import ctypes
import time
import numpy as np

cppyy.include('/usr/local/include/dlapi.h')
cppyy.load_library('/usr/local/lib/libdlapi')

dl = cppyy.gbl.dl

def handlePromise(pPromise):
    result = pPromise.wait()
    if result != dl.IPromise.Complete:
        buf = ctypes.create_string_buffer(512)
        blng = ctypes.c_ulong(512)
        pPromise.getLastError(buf, blng)
        pPromise.release()
        raise RuntimeError(buf.value)
    pPromise.release()
    
pGateway = dl.getGateway()
pGateway.queryUSBCameras()
nCameras = pGateway.getUSBCameraCount()
print('nCameras = {}'.format(nCameras))

pCamera = pGateway.getUSBCamera(0)
pCamera.initialize()

serial_buffer = ctypes.create_string_buffer(512)
buffer_length = ctypes.c_ulong(512)

pCamera.getSerial(serial_buffer, buffer_length)
print('Camera serial number: {}'.format(serial_buffer.value))

pSensor = pCamera.getSensor(0)
handlePromise(pSensor.abortExposure())

info = pSensor.getInfo()
subf = dl.TSubframe(0, 0, info.pixelsX, info.pixelsY, 1, 1)
handlePromise(pSensor.setSubframe(subf))

options = dl.TExposureOptions(0.1, 1, 1, 0, False, False, False)
handlePromise(pSensor.startExposure(options))

# Wait for the exposure to complete
while True:
    handlePromise(pCamera.queryStatus())
    status = pCamera.getStatus()
    if status.mainSensorState ==  dl.ISensor.ReadyToDownload:
        print("Data is ready to download.")
        break
    print("Waiting for exposure to complete...")
    time.sleep(0.3)
    
print("Starting download.")
pPromise = pSensor.startDownload()
while True:
    if pPromise.getStatus() == dl.IPromise.Complete:
        break
    print("Downloading...")
pPromise.release()

# Turn the buffer into a 1D array of unsigned shorts
pImg = pSensor.getImage()
rawdata = pImg.getBufferData()
n_data = pImg.getBufferLength()
print(f"Buffer length: {n_data}")
d = cppyy.ll.cast['ushort*'](rawdata)
d.reshape((n_data,))

# Turn the 1D list into a 2D numpy array.
data = np.reshape(np.array(d), (info.pixelsX, info.pixelsY))