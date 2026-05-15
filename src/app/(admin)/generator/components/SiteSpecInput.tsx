"use client";

import { useEffect, useState } from "react";
import SiteShapeSelector from "./SiteShapeSelector";

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

interface SiteSpecInputProps {
  site: SiteSpec;
  onSiteChange: (site: SiteSpec) => void;
}

export default function SiteSpecInput({ site, onSiteChange }: SiteSpecInputProps) {
  // Use site.shape_dimensions directly from props, with fallback
  const dimensions = site.shape_dimensions || { utara: 10, selatan: 10, barat: 9, timur: 9 };

  // Sync local state when shape_id changes - this ensures UI updates when shape changes
  useEffect(() => {
    // Trigger a recalculation by calling onDimensionsChange with current dimensions
    // This forces the parent to update and sync the footprint
    const shapeId = site.shape_id || "rectangle";
    const currentDims = site.shape_dimensions || {};

    // Recalculate footprint based on current shape and dimensions
    let footprint = 0;
    switch (shapeId) {
      case "rectangle":
      case "square":
        footprint = (currentDims.utara || currentDims.sisi || 0) * (currentDims.barat || currentDims.sisi || 0);
        break;
      case "trapezoid":
        footprint = ((currentDims.utara || 0) + (currentDims.selatan || 0)) / 2 * (currentDims.barat || 0);
        break;
      case "triangle":
        footprint = ((currentDims.selatan || 0) * (currentDims.barat || 0)) / 2;
        break;
      case "l-shape":
        const w1 = currentDims.utara_1 || 0;
        const w2 = currentDims.utara_2 || 0;
        const h1 = currentDims.barat || 0;
        const h2 = currentDims.timur_2 || 0;
        footprint = w1 * h1 + w2 * h2;
        break;
      case "pentagon":
      case "hexagon":
      case "polygon":
        const values = Object.values(currentDims).filter(v => typeof v === 'number');
        const avgSide = values.reduce((a, b) => a + b, 0) / (values.length || 1);
        footprint = avgSide * avgSide * 0.8;
        break;
      default:
        footprint = 90;
    }

    // Update footprint if it changed
    if (Math.abs(footprint - site.building_footprint_m2) > 0.1) {
      onSiteChange({
        ...site,
        building_footprint_m2: footprint,
      });
    }
  }, [site.shape_id]);

  const handleShapeSelect = (shapeId: string) => {
    // Set default dimensions for selected shape
    const defaultDimensions: Record<string, number> = {};

    switch (shapeId) {
      case "rectangle":
        defaultDimensions.utara = 10;
        defaultDimensions.selatan = 10;
        defaultDimensions.barat = 9;
        defaultDimensions.timur = 9;
        break;
      case "square":
        defaultDimensions.sisi = 10;
        break;
      case "trapezoid":
        defaultDimensions.utara = 8;
        defaultDimensions.selatan = 10;
        defaultDimensions.barat = 9;
        defaultDimensions.timur = 9;
        break;
      case "triangle":
        defaultDimensions.utara = 0;
        defaultDimensions.selatan = 10;
        defaultDimensions.barat = 9;
        defaultDimensions.timur = 9;
        break;
      case "l-shape":
        defaultDimensions.utara_1 = 6;
        defaultDimensions.utara_2 = 4;
        defaultDimensions.selatan = 10;
        defaultDimensions.barat = 9;
        defaultDimensions.timur_1 = 5;
        defaultDimensions.timur_2 = 4;
        break;
      case "pentagon":
        defaultDimensions.sisi_1 = 8;
        defaultDimensions.sisi_2 = 6;
        defaultDimensions.sisi_3 = 6;
        defaultDimensions.sisi_4 = 6;
        defaultDimensions.sisi_5 = 6;
        break;
      case "hexagon":
        defaultDimensions.sisi_1 = 7;
        defaultDimensions.sisi_2 = 6;
        defaultDimensions.sisi_3 = 6;
        defaultDimensions.sisi_4 = 7;
        defaultDimensions.sisi_5 = 6;
        defaultDimensions.sisi_6 = 6;
        break;
      default:
        defaultDimensions.utara = 10;
        defaultDimensions.selatan = 10;
        defaultDimensions.barat = 9;
        defaultDimensions.timur = 9;
    }

    // Calculate footprint for new shape
    let footprint = 0;
    switch (shapeId) {
      case "rectangle":
      case "square":
        footprint = (defaultDimensions.utara || defaultDimensions.sisi || 0) * (defaultDimensions.barat || defaultDimensions.sisi || 0);
        break;
      case "trapezoid":
        footprint = ((defaultDimensions.utara || 0) + (defaultDimensions.selatan || 0)) / 2 * (defaultDimensions.barat || 0);
        break;
      case "triangle":
        footprint = ((defaultDimensions.selatan || 0) * (defaultDimensions.barat || 0)) / 2;
        break;
      case "l-shape":
        footprint = (defaultDimensions.utara_1 || 0) * (defaultDimensions.barat || 0) + (defaultDimensions.utara_2 || 0) * (defaultDimensions.timur_2 || 0);
        break;
      case "pentagon":
      case "hexagon":
        const vals = Object.values(defaultDimensions);
        const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
        footprint = avg * avg * 0.8;
        break;
      default:
        footprint = 90;
    }

    onSiteChange({
      ...site,
      shape_id: shapeId,
      shape_dimensions: defaultDimensions,
      building_footprint_m2: footprint,
      building_width_m: defaultDimensions.utara || defaultDimensions.sisi || defaultDimensions.selatan || 0,
      building_depth_m: defaultDimensions.barat || defaultDimensions.sisi || 0,
    });
  };

  const handleDimensionsChange = (newDimensions: Record<string, number>) => {
    // Calculate footprint based on shape
    const shapeId = site.shape_id || "rectangle";
    let footprint = 0;

    switch (shapeId) {
      case "rectangle":
      case "square":
        footprint = (newDimensions.utara || newDimensions.sisi || 0) * (newDimensions.barat || newDimensions.sisi || 0);
        break;
      case "trapezoid":
        footprint = ((newDimensions.utara || 0) + (newDimensions.selatan || 0)) / 2 * (newDimensions.barat || 0);
        break;
      case "triangle":
        footprint = ((newDimensions.selatan || 0) * (newDimensions.barat || 0)) / 2;
        break;
      case "l-shape":
        const w1 = newDimensions.utara_1 || 0;
        const w2 = newDimensions.utara_2 || 0;
        const h1 = newDimensions.barat || 0;
        const h2 = newDimensions.timur_2 || 0;
        footprint = w1 * h1 + w2 * h2;
        break;
      case "pentagon":
      case "hexagon":
      case "polygon":
        const values = Object.values(newDimensions).filter(v => typeof v === 'number');
        const avgSide = values.reduce((a, b) => a + b, 0) / (values.length || 1);
        footprint = avgSide * avgSide * 0.8;
        break;
      default:
        footprint = 90;
    }

    onSiteChange({
      ...site,
      building_footprint_m2: footprint,
      building_width_m: newDimensions.utara || newDimensions.sisi || newDimensions.selatan || 0,
      building_depth_m: newDimensions.barat || newDimensions.sisi || 0,
      shape_dimensions: newDimensions,
    });
  };

  const handleTotalLandAreaChange = (area: number) => {
    onSiteChange({
      ...site,
      total_land_area_m2: area,
    });
  };

  return (
    <div className="space-y-4">
      <SiteShapeSelector
        selectedShape={site.shape_id || "rectangle"}
        onShapeSelect={handleShapeSelect}
        dimensions={dimensions}
        onDimensionsChange={handleDimensionsChange}
        totalLandArea={site.total_land_area_m2}
        onTotalLandAreaChange={handleTotalLandAreaChange}
        buildingFootprint={site.building_footprint_m2}
      />

      {/* Setbacks per Side */}
      <div className="border-t pt-4">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Setback per Sisi (m)
        </h4>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
              Utara (Depan)
            </label>
            <input
              type="number"
              step="0.5"
              value={site.setback_north_m}
              onChange={(e) =>
                onSiteChange({
                  ...site,
                  setback_north_m: parseFloat(e.target.value) || 0,
                })
              }
              className="w-full px-2 py-1 rounded border text-sm dark:bg-gray-700 dark:border-gray-600"
            />
          </div>

          <div>
            <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
              Selatan (Belakang)
            </label>
            <input
              type="number"
              step="0.5"
              value={site.setback_south_m}
              onChange={(e) =>
                onSiteChange({
                  ...site,
                  setback_south_m: parseFloat(e.target.value) || 0,
                })
              }
              className="w-full px-2 py-1 rounded border text-sm dark:bg-gray-700 dark:border-gray-600"
            />
          </div>

          <div>
            <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
              Timur
            </label>
            <input
              type="number"
              step="0.5"
              value={site.setback_east_m}
              onChange={(e) =>
                onSiteChange({
                  ...site,
                  setback_east_m: parseFloat(e.target.value) || 0,
                })
              }
              className="w-full px-2 py-1 rounded border text-sm dark:bg-gray-700 dark:border-gray-600"
            />
          </div>

          <div>
            <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
              Barat
            </label>
            <input
              type="number"
              step="0.5"
              value={site.setback_west_m}
              onChange={(e) =>
                onSiteChange({
                  ...site,
                  setback_west_m: parseFloat(e.target.value) || 0,
                })
              }
              className="w-full px-2 py-1 rounded border text-sm dark:bg-gray-700 dark:border-gray-600"
            />
          </div>
        </div>
      </div>

      {/* Orientation */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Orientasi Bangunan
        </label>
        <select
          value={site.orientation}
          onChange={(e) =>
            onSiteChange({
              ...site,
              orientation: e.target.value,
            })
          }
          className="w-full px-3 py-2 rounded border dark:bg-gray-700 dark:border-gray-600"
        >
          <option value="north">Hadap Utara</option>
          <option value="south">Hadap Selatan</option>
          <option value="east">Hadap Timur</option>
          <option value="west">Hadap Barat</option>
          <option value="north_east">Hadap Utara-Timur</option>
          <option value="north_west">Hadap Utara-Barat</option>
          <option value="south_east">Hadap Selatan-Timur</option>
          <option value="south_west">Hadap Selatan-Barat</option>
        </select>
      </div>

      {/* Slope Degree */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Kemiringan Lahan (°)
        </label>
        <input
          type="number"
          step="0.5"
          min="0"
          max="45"
          value={site.slope_degree}
          onChange={(e) =>
            onSiteChange({
              ...site,
              slope_degree: parseFloat(e.target.value) || 0,
            })
          }
          className="w-full px-3 py-2 rounded border dark:bg-gray-700 dark:border-gray-600"
        />
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          0° = datar, 15° = landai, 30°+ = curam
        </p>
      </div>
    </div>
  );
}
