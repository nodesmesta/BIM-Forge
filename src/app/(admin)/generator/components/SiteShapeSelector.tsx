"use client";

import { useState, useEffect, useMemo } from "react";

interface SiteShape {
  id: string;
  name: string;
  description: string;
  type: "rectangle" | "triangle" | "l-shape" | "trapezoid" | "polygon" | "circle";
  dimensionFields: {
    key: string;
    label: string;
    unit: string;
    description: string;
  }[];
}

interface SiteShapeSelectorProps {
  selectedShape: string;
  onShapeSelect: (shape: string) => void;
  dimensions: Record<string, number>;
  onDimensionsChange: (dimensions: Record<string, number>) => void;
  totalLandArea: number;
  onTotalLandAreaChange: (area: number) => void;
  buildingFootprint: number;
}

const SITE_SHAPES: SiteShape[] = [
  {
    id: "rectangle",
    name: "Rectangle",
    description: "Standard residential building shape",
    type: "rectangle",
    dimensionFields: [
      { key: "utara", label: "North (Front)", unit: "m", description: "Width of north side" },
      { key: "selatan", label: "South (Back)", unit: "m", description: "Width of south side" },
      { key: "barat", label: "West (Left)", unit: "m", description: "Length of west side" },
      { key: "timur", label: "East (Right)", unit: "m", description: "Length of east side" },
    ],
  },
  {
    id: "square",
    name: "Square",
    description: "Land in the shape of a square",
    type: "rectangle",
    dimensionFields: [
      { key: "sisi", label: "Panjang Sisi", unit: "m", description: "All sides equal length" },
    ],
  },
  {
    id: "trapezoid",
    name: "Trapezoid",
    description: "Land shaped as a trapezoid (west side perpendicular)",
    type: "trapezoid",
    dimensionFields: [
      { key: "utara", label: "North (Top)", unit: "m", description: "Width of north side (atas, sejajar selatan)" },
      { key: "selatan", label: "South (Bottom)", unit: "m", description: "Width of south side (bawah)" },
      { key: "barat", label: "West (Left)", unit: "m", description: "Length of west side (tegak lurus, tinggi)" },
      { key: "timur", label: "East (Right)", unit: "m", description: "Length of east side (miring)" },
    ],
  },
  {
    id: "l-shape",
    name: "L-Shape",
    description: "Land shaped like an L",
    type: "l-shape",
    dimensionFields: [
      { key: "utara_1", label: "North (Part 1)", unit: "m", description: "Width of upper left part" },
      { key: "utara_2", label: "North (Part 2)", unit: "m", description: "Width of upper right part" },
      { key: "selatan", label: "South", unit: "m", description: "Width of bottom part" },
      { key: "barat", label: "West", unit: "m", description: "Length of west side" },
      { key: "timur_1", label: "East (Part 1)", unit: "m", description: "Length of east side atas" },
      { key: "timur_2", label: "East (Part 2)", unit: "m", description: "Length of east side bawah" },
    ],
  },
  {
    id: "triangle",
    name: "Triangle",
    description: "Land shaped like a triangle",
    type: "triangle",
    dimensionFields: [
      { key: "utara", label: "Peak (North)", unit: "m", description: "Width at peak (can be 0 for acute triangle)" },
      { key: "selatan", label: "Alas (South)", unit: "m", description: "Width of triangle base" },
      { key: "barat", label: "Sisi West", unit: "m", description: "Length of left side" },
      { key: "timur", label: "East Side", unit: "m", description: "Length of right side" },
    ],
  },
  {
    id: "pentagon",
    name: "Pentagon",
    description: "Land shaped like a pentagon",
    type: "polygon",
    dimensionFields: [
      { key: "sisi_1", label: "Side 1 (North)", unit: "m", description: "Length of top side" },
      { key: "sisi_2", label: "Side 2 (East Top)", unit: "m", description: "Length of right side atas" },
      { key: "sisi_3", label: "Side 3 (East Bottom)", unit: "m", description: "Length of right side bawah" },
      { key: "sisi_4", label: "Side 4 (West Bawah)", unit: "m", description: "Length of left side bawah" },
      { key: "sisi_5", label: "Side 5 (West Atas)", unit: "m", description: "Length of left side atas" },
    ],
  },
  {
    id: "hexagon",
    name: "Hexagon",
    description: "Land shaped like a hexagon",
    type: "polygon",
    dimensionFields: [
      { key: "sisi_1", label: "Side 1", unit: "m", description: "Length of side 1" },
      { key: "sisi_2", label: "Side 2", unit: "m", description: "Length of side 2" },
      { key: "sisi_3", label: "Side 3", unit: "m", description: "Length of side 3" },
      { key: "sisi_4", label: "Side 4", unit: "m", description: "Length of side 4" },
      { key: "sisi_5", label: "Side 5", unit: "m", description: "Length of side 5" },
      { key: "sisi_6", label: "Side 6", unit: "m", description: "Length of side 6" },
    ],
  },
];

// Helper function to calculate scale factor that fits shape in viewbox
function calculateScaleFactor(points: { x: number; y: number }[], padding: number = 10): number {
  if (points.length === 0) return 1;

  let minX = Infinity, maxX = -Infinity;
  let minY = Infinity, maxY = -Infinity;

  for (const p of points) {
    minX = Math.min(minX, p.x);
    maxX = Math.max(maxX, p.x);
    minY = Math.min(minY, p.y);
    maxY = Math.max(maxY, p.y);
  }

  const shapeWidth = maxX - minX;
  const shapeHeight = maxY - minY;
  const availableWidth = 100 - padding * 2;
  const availableHeight = 80 - padding * 2;

  const scaleX = availableWidth / (shapeWidth || 1);
  const scaleY = availableHeight / (shapeHeight || 1);

  return Math.min(scaleX, scaleY); // Always scale to fit
}

// Helper function to scale and center shape in viewbox
function scaleAndCenterShape(points: { x: number; y: number }[], scaleFactor: number, padding: number = 10): string {
  if (points.length === 0) return "";

  // Find current bounds
  let minX = Infinity, maxX = -Infinity;
  let minY = Infinity, maxY = -Infinity;

  for (const p of points) {
    minX = Math.min(minX, p.x);
    maxX = Math.max(maxX, p.x);
    minY = Math.min(minY, p.y);
    maxY = Math.max(maxY, p.y);
  }

  // Calculate center offset
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;

  // Target center (center of viewbox)
  const targetCenterX = 50;
  const targetCenterY = 40;

  // Scale and translate
  const scaledPoints = points.map(p => ({
    x: targetCenterX + (p.x - centerX) * scaleFactor,
    y: targetCenterY + (p.y - centerY) * scaleFactor
  }));

  return scaledPoints.map(p => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ");
}

// Generate SVG points for rectangle
function getRectanglePoints(d: Record<string, number>): string {
  const utara = d.utara || 10; // Width at top (North)
  const selatan = d.selatan || 10; // Width at bottom (South)
  const barat = d.barat || 9; // Height on left (West)
  const timur = d.timur || 9; // Height on right (East)

  // Average width (utara/selatan) and height (barat/timur) for visualization
  const avgWidth = (utara + selatan) / 2;
  const avgHeight = (barat + timur) / 2;

  // Create points with relative dimensions
  const points = [
    { x: 0, y: 0 }, // top-left (North-West)
    { x: avgWidth, y: 0 }, // top-right (North-East)
    { x: avgWidth, y: avgHeight }, // bottom-right (South-East)
    { x: 0, y: avgHeight } // bottom-left (South-West)
  ];

  const scaleFactor = calculateScaleFactor(points);
  return scaleAndCenterShape(points, scaleFactor);
}

// Generate SVG points for trapezium (sisi barat tegak lurus)
function getTrapezoidPoints(d: Record<string, number>): string {
  const utara = d.utara || 10; // UTARA = ATAS (sebagaimana mestinya)
  const selatan = d.selatan || 8; // SELATAN = BAWAH
  const barat = d.barat || 9; // Tinggi (tegak lurus)

  // Create points with relative dimensions
  // West tegak lurus di kiri
  const points = [
    { x: 0, y: 0 }, // barat-atas (utara-kiri)
    { x: utara, y: 0 }, // utara-kanan
    { x: selatan, y: barat }, // selatan-kanan (timur-bawah)
    { x: 0, y: barat } // barat-bawah (selatan-kiri)
  ];

  const scaleFactor = calculateScaleFactor(points);
  return scaleAndCenterShape(points, scaleFactor);
}

// Generate SVG points for L-shape
function getLShapePoints(d: Record<string, number>): string {
  const utara1 = d.utara_1 || 6;
  const utara2 = d.utara_2 || 4;
  const selatan = d.selatan || 10;
  const barat = d.barat || 9;
  const timur1 = d.timur_1 || 5;
  const timur2 = d.timur_2 || 4;

  const totalWidth = utara1 + utara2;

  // L-shape points: start from top-left, go clockwise
  const points = [
    { x: 0, y: 0 }, // top-left
    { x: utara1, y: 0 }, // top of left arm
    { x: utara1, y: barat - timur2 }, // inner corner top
    { x: totalWidth, y: barat - timur2 }, // inner corner right
    { x: totalWidth, y: barat }, // bottom-right
    { x: 0, y: barat } // bottom-left
  ];

  const scaleFactor = calculateScaleFactor(points);
  return scaleAndCenterShape(points, scaleFactor);
}

// Generate SVG points for triangle
function getTrianglePoints(d: Record<string, number>): string {
  const utara = d.utara || 0; // Puncak (width at top)
  const selatan = d.selatan || 10; // Alas (width at bottom)
  const barat = d.barat || 9; // Tinggi

  // If utara is 0, it's a sharp triangle
  if (utara === 0) {
    const points = [
      { x: 0, y: 0 }, // top (puncak)
      { x: -selatan / 2, y: barat }, // bottom-left
      { x: selatan / 2, y: barat } // bottom-right
    ];

    const scaleFactor = calculateScaleFactor(points);
    return scaleAndCenterShape(points, scaleFactor);
  }

  // Otherwise, trapezoid-like triangle with flat top
  const points = [
    { x: -utara / 2, y: 0 }, // top-left
    { x: utara / 2, y: 0 }, // top-right
    { x: selatan / 2, y: barat }, // bottom-right
    { x: -selatan / 2, y: barat } // bottom-left
  ];

  const scaleFactor = calculateScaleFactor(points);
  return scaleAndCenterShape(points, scaleFactor);
}

// Generate SVG points for polygon (pentagon/hexagon - simplified)
function getPolygonPoints(d: Record<string, number>, sides: number): string {
  const values = Object.values(d).filter(v => typeof v === 'number');
  const avgSide = values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : 10;

  // Calculate radius based on side length (approximate for regular polygon)
  const radius = avgSide / (2 * Math.sin(Math.PI / sides));

  // Create points with relative dimensions
  const rawPoints: { x: number; y: number }[] = [];
  for (let i = 0; i < sides; i++) {
    const angle = (Math.PI * 2 * i / sides) - Math.PI / 2;
    const x = radius * Math.cos(angle);
    const y = radius * Math.sin(angle);
    rawPoints.push({ x, y });
  }

  const scaleFactor = calculateScaleFactor(rawPoints);
  return scaleAndCenterShape(rawPoints, scaleFactor);
}

export default function SiteShapeSelector({
  selectedShape,
  onShapeSelect,
  dimensions,
  onDimensionsChange,
  totalLandArea,
  onTotalLandAreaChange,
  buildingFootprint,
}: SiteShapeSelectorProps) {
  const selected = SITE_SHAPES.find((s) => s.id === selectedShape) || SITE_SHAPES[0];

  // Local state to track dimensions for better responsiveness
  const [localDimensions, setLocalDimensions] = useState<Record<string, number>>(() => ({ ...dimensions }));

  // Sync local dimensions when dimensions prop changes OR when selectedShape changes
  useEffect(() => {
    setLocalDimensions(dimensions);
  }, [dimensions, selectedShape]);

  const handleDimensionChange = (key: string, value: number) => {
    const newDimensions = {
      ...localDimensions,
      [key]: value,
    };
    setLocalDimensions(newDimensions);
    onDimensionsChange(newDimensions);
  };

  // Generate dynamic SVG based on selected shape and dimensions
  const dynamicSvg = useMemo(() => {
    const d = localDimensions;
    let points = "";
    let shapeElement: React.ReactNode;

    switch (selected.id) {
      case "rectangle":
      case "square":
        points = getRectanglePoints(d);
        shapeElement = (
          <polygon points={points} fill="none" stroke="#3b82f6" strokeWidth="2" />
        );
        break;
      case "trapezoid":
        points = getTrapezoidPoints(d);
        shapeElement = <polygon points={points} fill="none" stroke="#3b82f6" strokeWidth="2" />;
        break;
      case "l-shape":
        points = getLShapePoints(d);
        shapeElement = <polygon points={points} fill="none" stroke="#3b82f6" strokeWidth="2" />;
        break;
      case "triangle":
        points = getTrianglePoints(d);
        shapeElement = <polygon points={points} fill="none" stroke="#3b82f6" strokeWidth="2" />;
        break;
      case "pentagon":
        points = getPolygonPoints(d, 5);
        shapeElement = <polygon points={points} fill="none" stroke="#3b82f6" strokeWidth="2" />;
        break;
      case "hexagon":
        points = getPolygonPoints(d, 6);
        shapeElement = <polygon points={points} fill="none" stroke="#3b82f6" strokeWidth="2" />;
        break;
      default:
        points = getRectanglePoints(d);
        shapeElement = <polygon points={points} fill="none" stroke="#3b82f6" strokeWidth="2" />;
    }

    return (
      <svg viewBox="0 0 100 80" className="w-full h-32">
        {shapeElement}
        {/* North arrow indicator - only direction indicator needed */}
        <polygon points="50,3 53,8 47,8" fill="#3b82f6" />
        <text x="50" y="2" fontSize="6" fill="#3b82f6" textAnchor="middle" fontWeight="bold">N</text>
      </svg>
    );
  }, [localDimensions, selected.id]);

  // Calculate estimated building footprint based on shape
  const calculateFootprint = () => {
    switch (selected.type) {
      case "rectangle":
        return (localDimensions.utara || 0) * (localDimensions.barat || 0);
      case "trapezoid":
        return ((localDimensions.utara || 0) + (localDimensions.selatan || 0)) / 2 * (localDimensions.barat || 0);
      case "triangle":
        return ((localDimensions.selatan || 0) * (localDimensions.barat || 0)) / 2;
      case "l-shape":
        const w1 = localDimensions.utara_1 || 0;
        const w2 = localDimensions.utara_2 || 0;
        const h1 = localDimensions.barat || 0;
        const h2 = localDimensions.timur_2 || 0;
        return w1 * h1 + w2 * h2;
      case "polygon":
        const avgSide = Object.values(localDimensions).reduce((a, b) => a + b, 0) / Object.values(localDimensions).length;
        return avgSide * avgSide * 0.8;
      default:
        return (localDimensions.utara || 0) * (localDimensions.barat || 0);
    }
  };

  const estimatedFootprint = calculateFootprint();

  return (
    <div className="space-y-4">
      {/* Shape Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Land Shape
        </label>
        <select
          value={selectedShape}
          onChange={(e) => onShapeSelect(e.target.value)}
          className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white focus:ring-2 focus:ring-blue-500"
        >
          {SITE_SHAPES.map((shape) => (
            <option key={shape.id} value={shape.id}>
              {shape.name} - {shape.description}
            </option>
          ))}
        </select>
      </div>

      {/* Dimension Inputs */}
      <div className="border-t pt-4">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Dimensions {selected.name}
        </h4>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {selected.dimensionFields.map((field) => (
            <div key={field.key}>
              <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
                {field.label}
              </label>
              <input
                type="number"
                step="0.1"
                value={localDimensions[field.key] || 0}
                onChange={(e) => handleDimensionChange(field.key, parseFloat(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded border dark:bg-gray-700 dark:border-gray-600 text-sm"
                placeholder={`Masukkan ${field.label.toLowerCase()}`}
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{field.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Area Input */}
      <div className="border-t pt-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Total Land Area (m²) - From Certificate
            </label>
            <input
              type="number"
              value={totalLandArea}
              onChange={(e) => onTotalLandAreaChange(parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 rounded border dark:bg-gray-700 dark:border-gray-600"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              According to land certificate
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Estimated Building Footprint (m²)
            </label>
            <input
              type="number"
              value={estimatedFootprint.toFixed(1)}
              readOnly
              className="w-full px-3 py-2 rounded border dark:bg-gray-700 dark:border-gray-600 bg-gray-100 dark:bg-gray-800"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Calculated automatically from entered dimensions
            </p>
          </div>
        </div>
      </div>

      {/* Dynamic Visual Preview */}
      <div className="border-t pt-4">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Shape Preview (Proportional Scale)
        </h4>
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
          <div className="h-40 flex items-center justify-center">
            <div className="w-48 h-48">
              {dynamicSvg}
            </div>
          </div>
          <div className="mt-3 text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {selected.name} - Change dimension values to see shape changes
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
