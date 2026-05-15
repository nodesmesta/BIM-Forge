"use client";

import { useState, useEffect } from "react";
import SiteSpecInput from "./SiteSpecInput";
import LocationSelector from "./LocationSelector";

interface SiteSpec {
  total_land_area_m2: number;
  building_footprint_m2: number;
  building_width_m: number;
  building_depth_m: number;
  setback_north_m: number;
  setback_south_m: number;
  setback_east_m: number;
  setback_west_m: number;
  orientation: string;
  slope_degree: number;
  shape_id?: string;
  shape_dimensions?: Record<string, number>;
}

interface FloorSpec {
  floor_number: number;
  height_m: number;
  ceiling_height_m: number;
  purpose: string;
}

interface RoomRequirement {
  id: string;
  room_type: string;
  count: number;
  min_width_m: number;
  min_length_m: number;
  min_area_m2: number;
  preferred_floor: number;
  adjacent_to: string[];
  exterior_access: boolean;
  private: boolean;
}

interface Location {
  id: number;
  name: string;
  country: string;
  latitude: number;
  longitude: number;
  timezone: string;
}

interface StructuredFormProps {
  onGenerate: (specification: any) => void;
  isGenerating: boolean;
}

const ROOM_TYPES = [
  { value: "living_room", label: "Ruang Tamu" },
  { value: "dining_room", label: "Ruang Makan" },
  { value: "kitchen", label: "Dapur" },
  { value: "bedroom", label: "Kamar Tidur" },
  { value: "master_bedroom", label: "Kamar Tidur Utama" },
  { value: "bathroom", label: "Kamar Mandi" },
  { value: "office", label: "Kantor" },
  { value: "guest_room", label: "Kamar Tamu" },
  { value: "laundry", label: "Ruang Cuci" },
  { value: "storage", label: "Gudang" },
  { value: "garage", label: "Garasi" },
  { value: "carport", label: "Carport" },
];

const STYLE_TYPES = [
  { value: "modern", label: "Modern" },
  { value: "minimalist", label: "Minimalis" },
  { value: "tropical", label: "Tropis" },
  { value: "traditional", label: "Tradisional" },
  { value: "industrial", label: "Industrial" },
];

const ORIENTATIONS = [
  { value: "north", label: "Utara" },
  { value: "south", label: "Selatan" },
  { value: "east", label: "Timur" },
  { value: "west", label: "Barat" },
];

export default function StructuredForm({
  onGenerate,
  isGenerating,
}: StructuredFormProps) {
  const [expandedSection, setExpandedSection] = useState<string>("site");

  // Location state
  const [location, setLocation] = useState<Location | null>(null);

  // Site Specification
  const [site, setSite] = useState<SiteSpec>({
    total_land_area_m2: 120,
    building_footprint_m2: 90,
    building_width_m: 10,
    building_depth_m: 9,
    setback_north_m: 3,
    setback_south_m: 2,
    setback_east_m: 2,
    setback_west_m: 2,
    orientation: "north",
    slope_degree: 0.0,
    shape_id: "rectangle",
    shape_dimensions: { width: 10, depth: 9 },
  });

  // Project Info
  const [projectName, setProjectName] = useState("");
  const [style, setStyle] = useState("modern");
  const [floorCount, setFloorCount] = useState(2);

  // Floors
  const [floors, setFloors] = useState<FloorSpec[]>([
    { floor_number: 1, height_m: 3.5, ceiling_height_m: 3, purpose: "public" },
    { floor_number: 2, height_m: 3.2, ceiling_height_m: 2.8, purpose: "private" },
  ]);

  // Rooms
  const [rooms, setRooms] = useState<RoomRequirement[]>([]);

  // Temporary room form
  const [tempRoom, setTempRoom] = useState<Partial<RoomRequirement>>({
    room_type: "living_room",
    count: 1,
    min_width_m: 4,
    min_length_m: 4,
    min_area_m2: 16,
    preferred_floor: 1,
    adjacent_to: [],
    exterior_access: false,
    private: false,
  });

  // Update floors when floorCount changes
  useEffect(() => {
    const currentFloors = floors.map((f) => f.floor_number);
    const newFloors: FloorSpec[] = [];

    for (let i = 1; i <= floorCount; i++) {
      const existing = floors.find((f) => f.floor_number === i);
      if (existing) {
        newFloors.push(existing);
      } else {
        newFloors.push({
          floor_number: i,
          height_m: i === 1 ? 3.5 : 3.2,
          ceiling_height_m: i === 1 ? 3 : 2.8,
          purpose: i === 1 ? "public" : "private",
        });
      }
    }

    setFloors(newFloors);
  }, [floorCount]);

  const addRoom = () => {
    const newRoom: RoomRequirement = {
      id: Date.now().toString(),
      room_type: tempRoom.room_type || "living_room",
      count: tempRoom.count || 1,
      min_width_m: tempRoom.min_width_m || 3,
      min_length_m: tempRoom.min_length_m || 3,
      min_area_m2: tempRoom.min_area_m2 || 9,
      preferred_floor: tempRoom.preferred_floor || 1,
      adjacent_to: tempRoom.adjacent_to || [],
      exterior_access: tempRoom.exterior_access || false,
      private: tempRoom.private || false,
    };

    setRooms([...rooms, newRoom]);
    setTempRoom({
      room_type: "living_room",
      count: 1,
      min_width_m: 4,
      min_length_m: 4,
      min_area_m2: 16,
      preferred_floor: 1,
      adjacent_to: [],
      exterior_access: false,
      private: false,
    });
  };

  const removeRoom = (id: string) => {
    setRooms(rooms.filter((r) => r.id !== id));
  };

  const handleSiteChange = (updatedSite: SiteSpec) => {
    setSite(updatedSite);
  };

  const handleFloorChange = (
    floorNum: number,
    field: keyof FloorSpec,
    value: number | string
  ) => {
    setFloors(
      floors.map((f) =>
        f.floor_number === floorNum
        ? {
            ...f,
            [field]:
              typeof value === "string" ? value : parseFloat(value.toString()) || 0,
          }
        : f
      )
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const specification = {
      project_name: projectName || "Building Project",
      style,
      location: location ? {
        name: location.name,
        country: location.country,
        latitude: location.latitude,
        longitude: location.longitude,
        timezone: location.timezone,
      } : null,
      site,
      floors,
      rooms,
      circulation: {
        corridor_width_m: 1.2,
        staircase_width_m: 1.2,
        staircase_type: "straight",
      },
      zoning: {
        public: ["living_room", "dining_room", "kitchen"],
        private: ["bedroom", "master_bedroom", "bathroom"],
        service: ["laundry", "storage", "garage"],
      },
      constraints: {
        entrance_position: "front_center",
        kitchen_location: "rear",
        master_bedroom_location: "rear_corner",
      },
    };

    onGenerate(specification);
  };

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? "" : section);
  };

  const calculateTotalArea = () => {
    return rooms.reduce((sum, room) => sum + room.min_area_m2 * room.count, 0);
  };

  const calculateEfficiency = () => {
    const totalArea = calculateTotalArea();
    const footprint = site.building_footprint_m2;
    return ((totalArea / footprint) * 100).toFixed(1);
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-theme-md p-6">
      <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">
        Building Specification
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Project Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Project Name
            </label>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="Rumah Minimalis Modern"
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Style
            </label>
            <select
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white focus:ring-2 focus:ring-blue-500"
            >
              {STYLE_TYPES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Location Selector */}
        <LocationSelector location={location} onLocationChange={setLocation} />

        {/* Site Specification - Always Visible */}
        <div className="border rounded-lg p-4 space-y-4">
          <h3 className="font-medium text-gray-800 dark:text-white">
            1. Site & Building Dimensions
          </h3>

          <SiteSpecInput site={site} onSiteChange={handleSiteChange} />

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Number of Floors
            </label>
            <input
              type="number"
              min="1"
              max="5"
              value={floorCount}
              onChange={(e) => setFloorCount(parseInt(e.target.value) || 1)}
              className="w-full px-3 py-2 rounded border dark:bg-gray-700 dark:border-gray-600"
            />
          </div>
        </div>

        {/* Floor Specifications */}
        <div className="border rounded-lg overflow-hidden">
          <button
            type="button"
            onClick={() => toggleSection("floors")}
            className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 flex justify-between items-center"
          >
            <span className="font-medium text-gray-800 dark:text-white">
              2. Floor Specifications
            </span>
            <span className="text-gray-500">{expandedSection === "floors" ? "▲" : "▼"}</span>
          </button>

          {expandedSection === "floors" && (
            <div className="p-4 space-y-4">
              {floors.map((floor) => (
                <div key={floor.floor_number} className="border rounded p-3">
                  <div className="flex items-center mb-3">
                    <span className="font-medium mr-4">
                      Floor {floor.floor_number}
                    </span>
                    {floor.floor_number === 1 ? (
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                        Ground Floor
                      </span>
                    ) : (
                      <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">
                        Upper Floor
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">
                        Height (m)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        value={floor.height_m}
                        onChange={(e) =>
                          handleFloorChange(floor.floor_number, "height_m", e.target.value)
                        }
                        className="w-full px-2 py-1 rounded border text-sm dark:bg-gray-700 dark:border-gray-600"
                      />
                    </div>

                    <div>
                      <label className="block text-xs text-gray-600 mb-1">
                        Ceiling (m)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        value={floor.ceiling_height_m}
                        onChange={(e) =>
                          handleFloorChange(floor.floor_number, "ceiling_height_m", e.target.value)
                        }
                        className="w-full px-2 py-1 rounded border text-sm dark:bg-gray-700 dark:border-gray-600"
                      />
                    </div>

                    <div>
                      <label className="block text-xs text-gray-600 mb-1">
                        Purpose
                      </label>
                      <select
                        value={floor.purpose}
                        onChange={(e) =>
                          handleFloorChange(floor.floor_number, "purpose", e.target.value)
                        }
                        className="w-full px-2 py-1 rounded border text-sm dark:bg-gray-700 dark:border-gray-600"
                      >
                        <option value="public">Public</option>
                        <option value="private">Private</option>
                        <option value="service">Service</option>
                      </select>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Room Requirements */}
        <div className="border rounded-lg overflow-hidden">
          <button
            type="button"
            onClick={() => toggleSection("rooms")}
            className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 flex justify-between items-center"
          >
            <span className="font-medium text-gray-800 dark:text-white">
              3. Room Requirements
            </span>
            <span className="text-sm text-gray-500">
              {rooms.length} rooms | {calculateTotalArea()}m² total | {calculateEfficiency()}% efficiency
            </span>
          </button>

          {expandedSection === "rooms" && (
            <div className="p-4 space-y-4">
              {/* Add Room Form */}
              <div className="border rounded p-3 bg-gray-50 dark:bg-gray-800">
                <h4 className="text-sm font-medium mb-3">Add Room Type</h4>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Type</label>
                    <select
                      value={tempRoom.room_type}
                      onChange={(e) =>
                        setTempRoom({ ...tempRoom, room_type: e.target.value })
                      }
                      className="w-full px-2 py-1 rounded border text-sm dark:bg-gray-700 dark:border-gray-600"
                    >
                      {ROOM_TYPES.map((rt) => (
                        <option key={rt.value} value={rt.value}>
                          {rt.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Count</label>
                    <input
                      type="number"
                      min="1"
                      value={tempRoom.count}
                      onChange={(e) =>
                        setTempRoom({ ...tempRoom, count: parseInt(e.target.value) || 1 })
                      }
                      className="w-full px-2 py-1 rounded border text-sm dark:bg-gray-700 dark:border-gray-600"
                    />
                  </div>

                  <div>
                    <label className="block text-xs text-gray-600 mb-1">
                      Min Width (m)
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      value={tempRoom.min_width_m}
                      onChange={(e) =>
                        setTempRoom({
                          ...tempRoom,
                          min_width_m: parseFloat(e.target.value) || 0,
                        })
                      }
                      className="w-full px-2 py-1 rounded border text-sm dark:bg-gray-700 dark:border-gray-600"
                    />
                  </div>

                  <div>
                    <label className="block text-xs text-gray-600 mb-1">
                      Min Length (m)
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      value={tempRoom.min_length_m}
                      onChange={(e) =>
                        setTempRoom({
                          ...tempRoom,
                          min_length_m: parseFloat(e.target.value) || 0,
                        })
                      }
                      className="w-full px-2 py-1 rounded border text-sm dark:bg-gray-700 dark:border-gray-600"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-3">
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">
                      Min Area (m²)
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      value={tempRoom.min_area_m2}
                      onChange={(e) =>
                        setTempRoom({
                          ...tempRoom,
                          min_area_m2: parseFloat(e.target.value) || 0,
                        })
                      }
                      className="w-full px-2 py-1 rounded border text-sm dark:bg-gray-700 dark:border-gray-600"
                    />
                  </div>

                  <div>
                    <label className="block text-xs text-gray-600 mb-1">
                      Preferred Floor
                    </label>
                    <select
                      value={tempRoom.preferred_floor}
                      onChange={(e) =>
                        setTempRoom({
                          ...tempRoom,
                          preferred_floor: parseInt(e.target.value) || 1,
                        })
                      }
                      className="w-full px-2 py-1 rounded border text-sm dark:bg-gray-700 dark:border-gray-600"
                    >
                      {floors.map((f) => (
                        <option key={f.floor_number} value={f.floor_number}>
                          Floor {f.floor_number}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="flex items-end">
                    <label className="flex items-center text-sm text-gray-700 dark:text-gray-300">
                      <input
                        type="checkbox"
                        checked={tempRoom.exterior_access}
                        onChange={(e) =>
                          setTempRoom({
                            ...tempRoom,
                            exterior_access: e.target.checked,
                          })
                        }
                        className="mr-2"
                      />
                      Exterior Access
                    </label>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={addRoom}
                  className="w-full bg-green-600 hover:bg-green-700 text-white py-2 rounded text-sm"
                >
                  Add Room
                </button>
              </div>

              {/* Room List */}
              {rooms.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium">Added Rooms:</h4>
                  {rooms.map((room) => (
                    <div
                      key={room.id}
                      className="flex justify-between items-center border rounded p-2 bg-white dark:bg-gray-700"
                    >
                      <div className="text-sm">
                        <span className="font-medium">
                          {ROOM_TYPES.find((rt) => rt.value === room.room_type)?.label}
                        </span>{" "}
                        × {room.count} | {room.min_area_m2}m² | Floor {room.preferred_floor}
                        {room.exterior_access && (
                          <span className="text-xs text-blue-600 ml-2">Exterior</span>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={() => removeRoom(room.id)}
                        className="text-red-600 hover:text-red-800 text-sm"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Efficiency Warning */}
              {parseFloat(calculateEfficiency()) > 70 && (
                <div className="bg-yellow-100 border border-yellow-400 text-yellow-800 px-3 py-2 rounded text-sm">
                  Warning: Efficiency {calculateEfficiency()}% exceeds recommended 70%.
                  Consider reducing room requirements or increasing building footprint.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isGenerating || rooms.length === 0}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium py-3 px-6 rounded-lg transition-colors duration-200"
        >
          {isGenerating ? "Generating..." : "Generate Building Layout"}
        </button>
      </form>
    </div>
  );
}
