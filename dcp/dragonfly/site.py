from astropy.coordinates import EarthLocation
from astropy.time import Time
from astropy import units as u
import re
import datetime
import zoneinfo

class ObservingSite(object):
    
    def __init__(self, location, timezone):
        """_summary_

        Args:
            location (EarthLocation): AstroPy EarthLocation object.
            timezone (string): Named timezone e.g. 'US/Eastern'.
        """
        self.location = location
        self.timezone = timezone
    
    def data_in_astro_physics_mount_format(self):
        """Returns a dict of information correctly formatted for input to an Astro-Physics mount.
        
        Returns:
            _type_: _description_
        """
        
        earth_location = self.location
        
        # Latitude
        lat_str = earth_location.lat.to_string(unit=u.deg, sep=('*',':'))
        # Remove fractional arcseconds.
        lat_str = re.sub(r'^(.*)\.(\d*)', r'\1', lat_str)
        if earth_location.lat.deg > 0:
            lat_str = '+' + lat_str
        
        # Longitude
        lon_str = earth_location.lon.to_string(unit=u.deg, sep=('*',':'))
        if earth_location.lon.deg > -180 and earth_location.lon.deg < 0:
            lon_str = lon_str.replace('-', '+')
        # Remove fractional arcseconds.
        lon_str = re.sub(r'^(.*)\.(\d*)', r'\1', lon_str)
        
        # Current time and date
        now = datetime.datetime.now()
        current_time = now.strftime('%H:%M:%S')
        current_date = datetime.date.strftime(now, "%m/%d/%y")
        
        # UTC offset - note the AP convention is that this is positive for west of Greenwich.
        offset = datetime.datetime.now(zoneinfo.ZoneInfo(self.timezone)).utcoffset()
        offset_hours = int(offset.total_seconds()/3600)
        offset_hours = -1 * offset_hours
        utc_offset = '{:02}:00:00'.format(offset_hours)
        
        result = {}
        result['latitude'] = lat_str
        result['longitude'] = lon_str
        result['date'] = current_date
        result['local_time'] = current_time
        result['gmt_offset'] = utc_offset

        return result    
    

# Pre-defined locations where I could conceivably be using my AP mount.
oakville = ObservingSite(
            EarthLocation(lat=43.4675999625*u.deg, lon=-79.6877*u.deg, height=50*u.m),
            'US/Eastern')

mayhill = ObservingSite(
            EarthLocation(lat=32.7803*u.deg, lon=-105.8203*u.deg, height=2200*u.m),
            'US/Mountain')



    