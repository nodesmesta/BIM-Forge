# Agent Responsibilities Specification

## Arsitektur Multi-Agent Backend

Dokumen ini mendefinisikan tanggung jawab each agent agar tidak ada agent yang memproses data secara buta.

---

## TUPOKSI SETIAP AGENT

### 1. CoordinatorAgent
**Tanggung Jawab**: Layout + Arsitektur + Dinding
- [x] Generate layout (posisi ruang)
- [x] Generate SEMUA dinding (interior + exterior) secara SYNCHRONOUS
- [x] Generate doors dan windows
- [x] Return wall_bounds untuk setiap ruang

**Output**:
```python
{
    "layout_spec": {...},
    "floors_data": {...},  # Complete with walls
    "wall_bounds_by_space": {
        "living_room_1": {
            "bounds": {
                "north": y1,
                "south": y0,
                "east": x1,
                "west": x0
            }
        }
    }
}
```

**Yang TIDAK dilakukan**:
- Interior design details
- Furniture selection
- Material finishing specifications

---

### 2. SpaceAgents (BedroomAgent, dll)
**Tanggung Jawab**: Interior Design (Furniture + Lighting)
- [x] Terima wall_bounds dari CoordinatorAgent
- [x] Generate furniture dengan wall_anchor (relatif terhadap dinding)
- [x] Generate lighting preferences
- [x] Generate window/door preferences (bukan posisi actual)

**Input**:
```python
{
    "layout_config": {...},
    "wall_bounds_by_space": {...}  # CoordinatorAgent provides this
}
```

**Output**:
```python
{
    "space_type": "bedroom",
    "name": "Master Bedroom",
    "interior": {
        "furniture": [
            {
                "type": "bed",
                "width_m": 2.0,
                "depth_m": 1.6,
                "height_m": 0.5,
                "wall_anchor": "south",      # Against south wall
                "placement_hint": "center of south wall"
            },
            {
                "type": "wardrobe",
                "wall_anchor": "east",
                "placement_hint": "against east wall, left side"
            }
        ]
    }
}
```

**Yang TIDAK dilakukan**:
- Generate posisi absolute (x, y coordinates)
- Generate dinding
- Generate doors/windows positioning

---

### 3. IFCGeometryAgentV2
**Tanggung Jawab**: Convert Data ke IFC Geometry
- [x] Baca wall_bounds untuk setiap ruang
- [x] Interpretasi wall_anchor → koordinat absolute
- [x] Generate IFC elements (walls, furniture, etc.)
- [x] Shared wall geometry (dinding antara 2 ruang = 1 object)

**Input**:
```python
{
    "spaces": [
        {
            "name": "bedroom_1",
            "center_x": 2.5,
            "center_y": 3.0,
            "wall_bounds": {...},
            "interior": {
                "furniture": [
                    {
                        "wall_anchor": "south",
                        "placement_hint": "center"
                    }
                ]
            }
        }
    ]
}
```

**Output**: IFC file dengan geometry yang benar

---

## DATA FLOW (FIXED)

```
SEQUENCE BARU (BENAR):
┌─────────────────────────────────────────────────────────────┐
│ 1. CoordinatorAgent.generate_layout()                       │
│    - Generate layout_spec (posisi ruang)                   │
│    - Generate floors_data (layout + walls + doors + windows) │
│    - Generate wall_bounds_by_space                          │
│    → context["wall_bounds_by_space"] siap digunakan        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. SpaceAgents run                                          │
│    - Menerima wall_bounds dari context                      │
│    - Generate furniture DENGAN wall_anchor                  │
│    - furniture.type + wall_anchor + placement_hint         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. CoordinatorAgent.merge_space_designs()                  │
│    - Space designs dengan wall_anchor di-merge              │
│    - Wall boundaries sudah diketahui                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. IFCGeometryAgentV2.create_floor()                        │
│    - Baca wall_bounds dari SpaceData                       │
│    - Hitung posisi furniture dari wall_anchor              │
│    - Generate IFC geometry dengan posisi yang benar        │
└─────────────────────────────────────────────────────────────┘
```

---

## WALL_ANCHOR SPECIFICATION

### Valid Values
- `north`: Terhadap dinding utara (y = north_y - offset)
- `south`: Terhadap dinding selatan (y = south_y + offset)
- `east`: Terhadap dinding timur (x = east_x - offset)
- `west`: Terhadap dinding barat (x = west_x + offset)
- `center`: Di tengah ruangan (grid placement)

### Placement Hint Examples
- "center of north wall"
- "against east wall, left side"
- "center of room"
- "0.5m from west wall"

### Position Calculation Logic
```python
if wall_anchor == "north":
    pos_x = room_cx  # Default center
    pos_y = north_y - wall_offset
elif wall_anchor == "south":
    pos_x = room_cx
    pos_y = south_y + wall_offset
elif wall_anchor == "east":
    pos_x = east_x - wall_offset
    pos_y = room_cy
elif wall_anchor == "west":
    pos_x = west_x + wall_offset
    pos_y = room_cy
else:  # center
    # Grid placement fallback
```

---

## STAIRCASE IMPROVEMENTS

### Sebelum:
- Tangga hanya 1 box sederhana
- Hanya terhubung ke Floor 1
- Tidak ada detail

### Sesudah:
- IfcStair sebagai container
- IfcStairFlight untuk setiap flight (anak tangga)
- IfcSlab LANDING untuk bordes
- IfcRailing HANDRAIL untuk pagar tangga
- Terhubung ke SEMUA floors via IfcRelReferencedInSpatialStructure

### Terminologi Indonesia:
- Anak tangga = IfcStairFlight (tread/riser)
- Bordes/Landing = IfcSlab(PredefinedType="LANDING")
- Pagar Tangga = IfcRailing(PredefinedType="HANDRAIL")
- Tangga = IfcStair (container)

### IFC Relationships:
```python
# Tangga terhubung ke semua floors
for storey in storeys:
    file.createIfcRelReferencedInSpatialStructure(
        RelatingStructure=storey,
        RelatedElements=[staircase, flights, landings, railings]
    )
```

---

## FILES CHANGED

1. `coordinator_agent.py`
   - `generate_layout()`: Generate wall_bounds_by_space
   - `_generate_complete_floors_data()`: New method for synchronous wall generation
   - `_create_wall_bounds_for_spaces()`: New method
   - `_arrange_spaces_optimized()`: Include wall_bounds AND interior data in SpaceData

2. `space_agent.py`
   - `execute()`: Pass wall_bounds to space agents

3. `space_agents/bedroom_agent.py`
   - `_build_llm_prompt()`: Include wall boundaries info
   - `_generate_interior_details()`: Pass wall_bounds to LLM
   - `_normalize_llm_response()`: Include wall_anchor in output

4. `ifc_geometry_agent_v2.py`
   - `create_staircase()`: Complete rewrite with proper treads, risers, landings, railings
   - `create_furniture()`: Use wall_anchor for positioning
   - `_calculate_furniture_position_from_anchor()`: New function
   - `_parse_offset_from_hint()`: New function

5. `models/ifc_data.py`
   - `SpaceData`: Add wall_bounds field

---

## TESTING

Untuk verify bahwa perubahan bekerja:
1. Run generate task dengan multi-floor (2 lantai)
2. Check IFC output untuk:
   - Pintu: IfcDoor + IfcOpeningElement + IfcRelFillsElement
   - Jendela: IfcWindow + IfcOpeningElement + IfcRelFillsElement
   - Tangga: IfcStair + IfcStairFlight + IfcSlab(LANDING) + IfcRailing
   - Floor references: IfcRelReferencedInSpatialStructure untuk setiap floor

---

## ANTI-PATTERNS (Yang Dilarang)

1. **SpaceAgent generating absolute positions**
   - ❌ `position_x = 2.5` (absolute)
   - ✅ `wall_anchor = "south"` (relative)

2. **IFC agent guessing wall positions**
   - ❌ Calculate walls from furniture
   - ✅ Use wall_bounds from CoordinatorAgent

3. **Space agents running before wall generation**
   - ❌ SpaceAgents → CoordinatorAgent (walls) → IFC
   - ✅ CoordinatorAgent (walls) → SpaceAgents → IFC

4. **Duplicate wall geometry**
   - ❌ Wall_1 (Room A) + Wall_1_copy (Room B)
   - ✅ Wall_1 shared between Room A and Room B
