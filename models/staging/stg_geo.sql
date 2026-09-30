select
  geolocation_zip_code_prefix as zip_code_prefix,
  avg(geolocation_lat) as latitude,
  avg(geolocation_lng) as longitude
from raw.geolocation
group by 1

