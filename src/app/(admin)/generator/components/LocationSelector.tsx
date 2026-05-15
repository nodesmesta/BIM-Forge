"use client";

import { useState, useEffect, useRef } from "react";

interface Location {
  id: number;
  name: string;
  country: string;
  latitude: number;
  longitude: number;
  timezone: string;
}

interface LocationSelectorProps {
  location: Location | null;
  onLocationChange: (location: Location | null) => void;
}

// Use Nominatim (OpenStreetMap) for free geolocation data (no API key required)
const GEO_API_URL = "https://nominatim.openstreetmap.org/search";

export default function LocationSelector({ location, onLocationChange }: LocationSelectorProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Location[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    if (searchQuery.trim().length < 3) {
      setSuggestions([]);
      return;
    }

    debounceRef.current = setTimeout(() => {
      fetchLocations(searchQuery);
    }, 500);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [searchQuery]);

  const fetchLocations = async (query: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${GEO_API_URL}?q=${encodeURIComponent(query)}&format=json&limit=10&addressdetails=1`,
        {
          headers: {
            'Accept': 'application/json',
          }
        }
      );

      if (!response.ok) {
        throw new Error("Failed to fetch locations");
      }

      const data = await response.json();

      const locations: Location[] = (data || []).map((item: any) => ({
        id: item.place_id || Math.random(),
        name: item.display_name?.split(',')[0] || item.name || "Unknown",
        country: item.address?.country || item.address?.state || "Unknown",
        latitude: parseFloat(item.lat),
        longitude: parseFloat(item.lon),
        timezone: item.address?.timezone || "UTC",
      }));

      setSuggestions(locations.slice(0, 8));
    } catch (err) {
      console.error("Error fetching locations:", err);
      setError("Gagal memuat lokasi. Silakan coba lagi.");
      setSuggestions([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelect = (selectedLocation: Location) => {
    onLocationChange(selectedLocation);
    setSearchQuery(selectedLocation.name);
    setShowDropdown(false);
    setSuggestions([]);
  };

  const handleClear = () => {
    onLocationChange(null);
    setSearchQuery("");
    setSuggestions([]);
  };

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        Lokasi Proyek
      </label>

      <div className="relative">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setShowDropdown(true);
            }}
            onFocus={() => {
              if (suggestions.length > 0) setShowDropdown(true);
            }}
            placeholder="Cari kota/kabupaten (minimal 3 karakter)..."
            className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />

          {location && (
            <button
              type="button"
              onClick={handleClear}
              className="px-3 py-2 text-sm text-red-600 hover:text-red-800 dark:text-red-400"
            >
              Clear
            </button>
          )}
        </div>

        {isLoading && (
          <div className="absolute right-3 top-3">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
          </div>
        )}

        {error && (
          <p className="text-sm text-red-600 dark:text-red-400 mt-1">{error}</p>
        )}

        {/* Dropdown Suggestions */}
        {showDropdown && suggestions.length > 0 && (
          <div className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-64 overflow-y-auto">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion.id}
                type="button"
                onClick={() => handleSelect(suggestion)}
                className="w-full px-4 py-3 text-left hover:bg-blue-50 dark:hover:bg-gray-700 transition-colors border-b border-gray-200 dark:border-gray-700 last:border-0"
              >
                <div className="font-medium text-gray-800 dark:text-white">
                  {suggestion.name}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {suggestion.country}
                </div>
                <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                  Lat: {suggestion.latitude.toFixed(4)}, Lng: {suggestion.longitude.toFixed(4)}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Selected Location Info */}
      {location && (
        <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <p className="font-medium text-blue-900 dark:text-blue-100">
            {location.name}, {location.country}
          </p>
          <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
            Koordinat: {location.latitude.toFixed(4)}°N, {location.longitude.toFixed(4)}°E
          </p>
        </div>
      )}

      {/* Info text */}
      {!location && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
          Lokasi akan digunakan untuk menghitung pencahayaan matahari, orientasi bangunan optimal,
          dan menyesuaikan dengan standar IFC setempat.
        </p>
      )}

      {/* Click outside to close dropdown */}
      {showDropdown && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowDropdown(false)}
        />
      )}
    </div>
  );
}
