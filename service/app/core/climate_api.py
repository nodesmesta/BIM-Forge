"""
Climate data from Open-Meteo Historical Weather API (ERA5 archive).

Daily aggregates for a full calendar year are normalized into the same
architectural profile shape used by the rest of the pipeline.
"""

import httpx
from typing import Dict, Optional, Any, List


class ClimateAPIError(Exception):
    """Raised when climate API call fails."""
    pass


class ClimateAPI:
    """
    Climate data client backed by Open-Meteo archive (ERA5).

    Open-Meteo archive: https://open-meteo.com/en/docs/historical-weather-api
    """

    def __init__(self, api_key: str = None):
        pass

    def _open_meteo_to_nasa_parameter_shape(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        daily = payload.get("daily") or {}
        times = daily.get("time") or []
        tmax = daily.get("temperature_2m_max") or []
        tmin = daily.get("temperature_2m_min") or []
        precip = daily.get("precipitation_sum") or []
        rh = daily.get("relative_humidity_2m_mean") or []
        wind = daily.get("windspeed_10m_mean") or []
        sw = daily.get("shortwave_radiation_sum") or []

        t2m: Dict[str, float] = {}
        prectot: Dict[str, float] = {}
        rh2m: Dict[str, float] = {}
        ws10m: Dict[str, float] = {}
        solar_kw: Dict[str, float] = {}

        for i, iso in enumerate(times):
            if not iso or len(iso) < 10:
                continue
            key = f"{iso[0:4]}{iso[5:7]}{iso[8:10]}"
            a = tmax[i] if i < len(tmax) else None
            b = tmin[i] if i < len(tmin) else None
            if a is not None and b is not None:
                t2m[key] = (float(a) + float(b)) / 2.0
            elif a is not None:
                t2m[key] = float(a)
            elif b is not None:
                t2m[key] = float(b)
            else:
                continue

            p = precip[i] if i < len(precip) else None
            prectot[key] = float(p) if p is not None else 0.0

            h = rh[i] if i < len(rh) else None
            if h is not None:
                rh2m[key] = float(h)

            w = wind[i] if i < len(wind) else None
            if w is not None:
                ws10m[key] = float(w)

            s = sw[i] if i < len(sw) else None
            if s is not None:
                solar_kw[key] = float(s) / 3.6

        return {"properties": {"parameter": {
            "T2M": t2m,
            "PRECTOTCORR": prectot,
            "RH2M": rh2m,
            "WS10M": ws10m,
            "ALLSKY_SFC_SW_DWN": solar_kw,
        }}}

    async def get_climate_data(
        self,
        latitude: float,
        longitude: float,
        city_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query climate data by GPS coordinates (Open-Meteo ERA5 daily archive).

        Raises:
            ClimateAPIError: If API call fails or returns invalid data
        """
        if not (-90 <= latitude <= 90):
            raise ClimateAPIError(f"Invalid latitude: {latitude}. Must be between -90 and 90.")
        if not (-180 <= longitude <= 180):
            raise ClimateAPIError(f"Invalid longitude: {longitude}. Must be between -180 and 180.")

        daily_vars = ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "relative_humidity_2m_mean",
            "windspeed_10m_mean",
            "shortwave_radiation_sum",
        ])

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                "https://archive-api.open-meteo.com/v1/archive",
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "start_date": "2023-01-01",
                    "end_date": "2023-12-31",
                    "daily": daily_vars,
                },
            )

        if response.status_code != 200:
            raise ClimateAPIError(
                f"Open-Meteo archive returned status {response.status_code}: {response.text}"
            )
        payload = response.json()
        nasa_like = self._open_meteo_to_nasa_parameter_shape(payload)
        normalized = self._normalize_nasa_response(
            nasa_like, latitude, longitude, city_name, source_label="Open-Meteo ERA5 (2023 daily archive)"
        )
        return normalized

    def _normalize_nasa_response(
        self,
        data: Dict[str, Any],
        latitude: float,
        longitude: float,
        city_name: Optional[str],
        source_label: str = "climate archive",
    ) -> Dict[str, Any]:
        """
        Normalize daily parameter series into the architectural climate profile.
        """
        try:
            # NASA POWER returns daily data in properties.parameter
            parameters = data.get("properties", {}).get("parameter", {})

            
            # Extract daily data
            # T2M: Temperature at 2 Meters (C)
            # PRECTOTCORR: Precipitation Corrected (mm/day)
            # RH2M: Relative Humidity at 2 Meters (%)
            # WS10M: Wind Speed at 10 Meters (m/s)
            # ALLSKY_SFC_SW_DWN: All Sky Surface Shortwave Downward Irradiance (kW-hr/m^2/day)

            temp_daily = parameters.get("T2M", {})
            precip_daily = parameters.get("PRECTOTCORR", {})
            humidity_daily = parameters.get("RH2M", {})
            wind_daily = parameters.get("WS10M", {})
            solar_daily = parameters.get("ALLSKY_SFC_SW_DWN", {})

            
            if not temp_daily or not precip_daily:
                raise ClimateAPIError("Climate response missing essential temperature or precipitation series")

            # Convert daily data to monthly averages/totals
            temp_monthly = self._daily_to_monthly_avg(temp_daily)
            precip_monthly = self._daily_to_monthly_total(precip_daily)  # mm/month
            humidity_monthly = self._daily_to_monthly_avg(humidity_daily)
            wind_monthly = self._daily_to_monthly_avg(wind_daily)
            solar_monthly = self._daily_to_monthly_avg(solar_daily)

            
            # Calculate annual statistics
            annual_avg_temp = sum(temp_monthly) / len(temp_monthly)
            min_temp = min(temp_monthly)
            max_temp = max(temp_monthly)

            annual_rainfall = sum(precip_monthly)
            max_daily_rain = max(precip_monthly) / 30  # Approximate daily max

            avg_humidity = sum(humidity_monthly) / len(humidity_monthly) if humidity_monthly else 70
            avg_wind = sum(wind_monthly) / len(wind_monthly) if wind_monthly else 3.0
            avg_solar = sum(solar_monthly) / len(solar_monthly) if solar_monthly else 5.0

            # Classify climate zone using Köppen
            climate_zone = self._classify_climate_zone(temp_monthly, precip_monthly)

            # Identify wet and dry seasons
            wet_season = self._identify_wet_season(precip_monthly)
            dry_season = self._identify_dry_season(precip_monthly)

            # Estimate prevailing wind direction (NASA POWER provides direction separately)
            prevailing_wind = self._estimate_wind_direction(latitude)

            return {
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "city": city_name or "Unknown"
                },
                "climate_zone": climate_zone,
                "temperature": {
                    "annual_avg": round(annual_avg_temp, 1),
                    "min": round(min_temp, 1),
                    "max": round(max_temp, 1),
                    "daily_range_avg": round(annual_avg_temp * 0.25, 1)  # Estimated diurnal range
                },
                "rainfall": {
                    "total_mm": round(annual_rainfall, 1),
                    "days_with_rain": round(annual_rainfall / 10),  # Estimate: 10mm per rainy day
                    "max_daily_mm": round(max_daily_rain, 1),
                    "wet_season": wet_season,
                    "dry_season": dry_season
                },
                "humidity": {
                    "annual_avg": round(avg_humidity, 0)
                },
                "wind": {
                    "prevailing_direction": prevailing_wind,
                    "avg_speed_ms": round(avg_wind, 1)
                },
                "solar": {
                    "peak_sun_hours_avg": round(avg_solar, 1),
                    "uv_index_max": round(self._solar_to_uv(avg_solar), 1)
                },
                "recommendations": self._generate_recommendations(
                    climate_zone,
                    temp_monthly,
                    precip_monthly,
                    prevailing_wind
                ),
                "source": source_label
            }

        except ClimateAPIError:
            raise
        except Exception as e:
            raise ClimateAPIError(f"Error processing climate response: {str(e)}")

    def _daily_to_monthly_avg(self, daily_data: Dict[str, float]) -> List[float]:
        """Convert daily data to monthly averages."""
        monthly_totals = {}
        monthly_counts = {}

        for date_str, value in daily_data.items():
            # Format: YYYYMMDD
            if len(date_str) != 8:
                continue

            year_month = date_str[:6]  # YYYYMM
            if year_month not in monthly_totals:
                monthly_totals[year_month] = 0
                monthly_counts[year_month] = 0

            monthly_totals[year_month] += value
            monthly_counts[year_month] += 1

        # Calculate monthly averages
        monthly_avgs = []
        for year_month in sorted(monthly_totals.keys()):
            if monthly_counts[year_month] > 0:
                monthly_avgs.append(monthly_totals[year_month] / monthly_counts[year_month])
            else:
                monthly_avgs.append(0)

        # Return only 12 months (if we have data for full year)
        return monthly_avgs[:12]

    def _daily_to_monthly_total(self, daily_data: Dict[str, float]) -> List[float]:
        """Convert daily data to monthly totals."""
        monthly_totals = {}

        for date_str, value in daily_data.items():
            # Format: YYYYMMDD
            if len(date_str) != 8:
                continue

            year_month = date_str[:6]  # YYYYMM
            if year_month not in monthly_totals:
                monthly_totals[year_month] = 0

            monthly_totals[year_month] += value

        # Return monthly totals
        monthly_values = [monthly_totals[year_month] for year_month in sorted(monthly_totals.keys())]
        return monthly_values[:12]

    def _classify_climate_zone(
        self,
        temp_monthly: List[float],
        precip_monthly: List[float]
    ) -> str:
        """
        Classify climate zone using simplified Köppen classification.
        """
        avg_temp = sum(temp_monthly) / len(temp_monthly)
        total_rain = sum(precip_monthly)
        min_temp = min(temp_monthly)
        max_temp = max(temp_monthly)

        # Tropical: All months > 18°C
        if min_temp >= 18:
            if total_rain >= 2000:
                return "tropical monsoon"
            elif total_rain >= 1500:
                return "tropical rainforest"
            else:
                return "tropical savanna"

        # Arid: Low rainfall
        if total_rain < 500:
            if avg_temp >= 18:
                return "hot arid"
            else:
                return "cold arid"

        # Temperate: Moderate temps
        if 10 <= avg_temp < 18:
            return "temperate"

        # Continental: Large temperature range
        if max_temp - min_temp > 20:
            return "continental"

        # Default to temperate
        return "temperate"

    def _identify_wet_season(self, precip_monthly: List[float]) -> List[str]:
        """Identify months with high rainfall."""
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        avg_rain = sum(precip_monthly) / len(precip_monthly)
        wet_threshold = avg_rain * 1.5

        wet_months = [months[i] for i, rain in enumerate(precip_monthly)
                     if rain > wet_threshold]

        return wet_months if wet_months else ["No distinct wet season"]

    def _identify_dry_season(self, precip_monthly: List[float]) -> List[str]:
        """Identify months with low rainfall."""
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        avg_rain = sum(precip_monthly) / len(precip_monthly)
        dry_threshold = avg_rain * 0.5

        dry_months = [months[i] for i, rain in enumerate(precip_monthly)
                     if rain < dry_threshold]

        return dry_months if dry_months else ["No distinct dry season"]

    def _estimate_wind_direction(self, latitude: float) -> str:
        """
        Estimate prevailing wind direction based on latitude (general patterns).
        """
        # General global wind patterns
        abs_lat = abs(latitude)

        if abs_lat < 30:
            # Trade winds zone
            return "east" if latitude > 0 else "east"
        elif abs_lat < 60:
            # Westerlies zone
            return "west"
        else:
            # Polar easterlies
            return "east"

    def _solar_to_uv(self, solar_radiation: float) -> float:
        """
        Convert solar radiation (kWh/m²/day) to approximate UV index.
        """
        # Rough conversion: UV index ≈ solar radiation * 0.15
        return round(solar_radiation * 0.15, 1)

    
    def _generate_recommendations(
        self,
        climate_zone: str,
        temps: List[float],
        rainfall: List[float],
        wind_direction: str
    ) -> Dict[str, str]:
        """
        Generate architectural recommendations based on climate data.
        """
        recommendations = {}

        # Ventilation recommendations
        if "tropical" in climate_zone:
            recommendations["ventilation"] = (
                "Natural cross ventilation is mandatory. Design windows on opposite walls "
                f"aligned with {wind_direction} prevailing wind. Consider operable windows "
                "covering 20-25% of wall area."
            )
        elif "arid" in climate_zone:
            recommendations["ventilation"] = (
                "Night flushing ventilation strategy recommended. Small daytime openings "
                "with large nighttime ventilation to cool thermal mass. Consider "
                "courtyard design for stack effect."
            )
        else:
            recommendations["ventilation"] = (
                "Adjustable ventilation for seasonal variation. Maximize summer cross "
                "ventilation while allowing winter heat retention."
            )

        # Roof recommendations
        total_rain = sum(rainfall)
        if total_rain > 2000:
            recommendations["roof_design"] = (
                f"Steep roof pitch (minimum 30°) required for rapid rain runoff. "
                "Deep overhangs (600-800mm) for rain protection and shade. "
                "Consider metal or clay tile with excellent drainage."
            )
        elif total_rain > 1000:
            recommendations["roof_design"] = (
                "Medium roof pitch (20-30°) adequate. Overhangs of 400-600mm recommended. "
                "Ensure proper gutter system for moderate rainfall."
            )
        else:
            recommendations["roof_design"] = (
                "Low pitch or flat roof acceptable (10-15°). Focus on insulation "
                "rather than rain drainage. Minimal overhangs needed."
            )

        # Window recommendations
        avg_temp = sum(temps) / len(temps)
        if avg_temp > 25:
            recommendations["window_placement"] = (
                "Minimize west-facing windows (afternoon heat gain). Maximize north/south "
                "exposure with proper shading. Use high-performance glass with low SHGC "
                "(Solar Heat Gain Coefficient < 0.3)."
            )
        else:
            recommendations["window_placement"] = (
                "Balance solar gain between seasons. North-facing windows for winter "
                "heat (southern hemisphere) with removable shading for summer."
            )

        # Material recommendations
        if "tropical" in climate_zone:
            recommendations["materials"] = (
                "Moisture-resistant materials essential: ceramic tile floors, "
                "brick/block walls with moisture barrier, treated wood for any "
                "structural elements. Avoid carpet and gypsum in wet areas."
            )
        elif "arid" in climate_zone:
            recommendations["materials"] = (
                "High thermal mass materials: concrete, stone, adobe. "
                "Light colors for exterior to reflect solar radiation. "
                "Insulation on exterior side of thermal mass."
            )
        else:
            recommendations["materials"] = (
                "Balanced approach: moderate insulation with some thermal mass. "
                "Consider local materials appropriate for regional climate."
            )

        # Elevation/flood recommendations
        if total_rain > 2500:
            recommendations["elevation"] = (
                "Minimum 500mm elevation above grade recommended for flood protection. "
                "Ensure proper site drainage away from building. Consider raised "
                "foundation in flood-prone areas."
            )
        else:
            recommendations["elevation"] = (
                "Standard 300mm elevation adequate. Ensure proper grading "
                "for water runoff."
            )

        return recommendations
