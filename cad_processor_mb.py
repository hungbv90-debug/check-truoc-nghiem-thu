import ezdxf
import re
from ezdxf.math import Vec3

def strip_formatting(text):
    if not text: return ""
    text = re.sub(r'\\[pP][xXiItT][^;]*;', '', text)
    text = re.sub(r'\\[fF][^;]+;', '', text)
    text = re.sub(r'\\[L|l|K|k|O|o|X|x]', '', text)
    text = re.sub(r'\\[C|c|H|h|T|t|Q|q|W|w|A|a][^;]+;', '', text)
    text = re.sub(r'\\[C|c|H|h|T|t|Q|q|W|w|A|a]\d+', '', text)
    text = text.replace('{', '').replace('}', '')
    return text.strip()

def parse_connection_cores(line):
    parts = line.split('-')
    if len(parts) < 2:
        return []
    
    left_part = strip_formatting(parts[0]).replace(" ", "")
    right_part = strip_formatting(parts[1]).replace(" ", "")
    
    if not left_part or not right_part:
        return []
    
    def parse_side(side_str):
        m_range = re.search(r'\.(\d+)/(\d+)$', side_str)
        if m_range:
            base = side_str[:m_range.start()]
            return base, int(m_range.group(1)), int(m_range.group(2))
        m_single = re.search(r'\.(\d+)$', side_str)
        if m_single:
            base = side_str[:m_single.start()]
            val = int(m_single.group(1))
            return base, val, val
        return side_str, None, None

    L_base, L_start, L_end = parse_side(left_part)
    R_base, R_start, R_end = parse_side(right_part)
    
    if L_start is not None and R_start is not None:
        L_cores = L_end - L_start + 1
        R_cores = R_end - R_start + 1
        num_cores = max(L_cores, R_cores)
        keys = []
        for i in range(num_cores):
            L_val = L_start + i
            R_val = R_start + i
            keys.append(f"{L_base}.{L_val}-{R_base}.{R_val}")
        return keys
    elif L_start is not None:
        num_cores = L_end - L_start + 1
        keys = []
        for i in range(num_cores):
            keys.append(f"{L_base}.{L_start + i}-{R_base}")
        return keys
    elif R_start is not None:
        num_cores = R_end - R_start + 1
        keys = []
        for i in range(num_cores):
            keys.append(f"{L_base}-{R_base}.{R_start + i}")
        return keys
    else:
        return [f"{L_base}-{R_base}"]

def parse_block_attrs(raw_content):
    if not raw_content: return "", ""
    raw_content_normalized = raw_content.replace('^J', '\\P').replace('\n', '\\P')
    text = strip_formatting(raw_content_normalized)
    parts = [p.strip() for p in text.split('\\') if p.strip()]
    
    box_code = ""
    capacity_text = ""
    
    # If the first part contains the cabinet name, skip it. Otherwise, process all parts!
    start_idx = 1 if parts and re.search(r'P\d{2,4}\.\d{4}', parts[0]) else 0
    
    for part in parts[start_idx:]:
        val = part
        if val.startswith('P') or val.startswith('p'):
            if len(val) > 1 and val[1].upper() in ['C', 'H', 'S', 'M', 'T', 'O', 'B', 'F', 'D', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
                val = val[1:]
                
        if 'SP' in val.upper() or '1:' in val.upper() or '2X' in val.upper() or 'CAP' in val.upper():
            if capacity_text:
                capacity_text = f"{capacity_text} {val}"
            else:
                capacity_text = val
        elif any(val.upper().startswith(x) for x in ['H', 'C', 'M', 'T', 'O', 'B', 'F', 'D']):
            box_code = val
        else:
            if not box_code:
                box_code = val
                
    return box_code, capacity_text

def extract_numeric_capacity(cap_text):
    if not cap_text: return 0
    cap_text_clean = str(cap_text).strip().upper()
    
    total = 0
    # 1. Parse stage-colon formats first: e.g. "2xSP2:8" -> 2 * 8 = 16, "SP1 2x:16" -> 32, "SP2:8" -> 8
    mul_colon_pattern = r'(\d+)\s*[xX]\s*(?:SP\d+\s*)?:\s*(\d+)'
    for m in re.finditer(mul_colon_pattern, cap_text_clean):
        total += int(m.group(1)) * int(m.group(2))
        
    cap_text_remaining = re.sub(mul_colon_pattern, '', cap_text_clean)
    
    single_colon_pattern = r'SP\d+:(\d+)'
    for m in re.finditer(single_colon_pattern, cap_text_remaining):
        total += int(m.group(1))
        
    cap_text_remaining = re.sub(single_colon_pattern, '', cap_text_remaining)
    
    # 2. Parse traditional formats: e.g. "2xSP2 1:8" -> 16
    mul_pattern = r'(\d+)\s*[xX]\s*(?:SP\d+\s+)?(?:1:)?(\d+)'
    for m in re.finditer(mul_pattern, cap_text_remaining):
        total += int(m.group(1)) * int(m.group(2))
        
    cap_text_remaining = re.sub(mul_pattern, '', cap_text_remaining)
    
    single_pattern = r'1:(\d+)'
    for m in re.finditer(single_pattern, cap_text_remaining):
        total += int(m.group(1))
        
    cap_text_remaining = re.sub(single_pattern, '', cap_text_remaining)
    
    if total == 0:
        num_match = re.search(r'\d+', cap_text_remaining)
        if num_match:
            return int(num_match.group(0))
            
    return total

def format_cad_capacity_display(cap_text):
    if not cap_text: return ""
    num = extract_numeric_capacity(cap_text)
    if num == 0: return cap_text
    
    lbl = ""
    if "SP2" in cap_text.upper():
        lbl = "SP2"
    elif "SP1" in cap_text.upper():
        lbl = "SP1"
        
    base_display = f"{num} {lbl}".strip()
    return f"{base_display} ({cap_text})"

def extract_gpon_topology(dxf_path):
    try:
        doc = ezdxf.readfile(dxf_path)
    except Exception as e:
        print(f"Error reading DXF: {e}")
        return {}
        
    blocks_info = []
    lines_pts = []
    splices_texts = []

    # Select layouts that actually contain GPON cabinet blocks (e.g. matching P\d{2,4}\.\d{4})
    # to avoid scanning empty layouts or unrelated sheets, while ensuring ModelSpace is scanned if it has the design.
    gpon_layouts = []
    for l in doc.layouts:
        has_gpon = False
        try:
            for t in l.query('TEXT MTEXT'):
                raw = t.text if t.dxftype() == 'MTEXT' else t.dxf.text
                if raw and re.search(r'P\d{2,4}\.\d{4}', raw):
                    has_gpon = True
                    break
        except:
            pass
        if has_gpon:
            gpon_layouts.append(l)
            
    layouts = gpon_layouts if gpon_layouts else [doc.modelspace()]
    # Sort layouts so that 'MODEL' space is processed first,
    # allowing paper space print layouts to overwrite/update with official sheet values.
    try:
        layouts.sort(key=lambda l: 0 if getattr(l, 'name', '').upper() == 'MODEL' else 1)
    except:
        pass

    attributes_texts = []

    def process_layout(layout, layout_name="Model"):
        lbs_info = []
        llns_pts = []
        lspls_texts = []
        lattrs_texts = []
        if layout is None: 
            return lbs_info, llns_pts, lspls_texts, lattrs_texts
        
        for entity in layout.query('LINE LWPOLYLINE'):
            if entity.dxftype() == 'LINE':
                llns_pts.append((entity.dxf.start, entity.dxf.end))
            elif entity.dxftype() == 'LWPOLYLINE':
                pts = entity.get_points()
                if len(pts) >= 2:
                    llns_pts.append((Vec3(pts[0][0], pts[0][1], 0), Vec3(pts[-1][0], pts[-1][1], 0)))

        for text_entity in layout.query('TEXT MTEXT'):
            raw_content = text_entity.text if text_entity.dxftype() == 'MTEXT' else text_entity.dxf.text
            content = strip_formatting(raw_content)
            insert_pt = text_entity.dxf.insert
            
            # Robust plan code regex: supports 2, 3, or 4 digits (e.g. P45, P132, P1002)
            if re.search(r'P\d{2,4}\.\d{4}', content):
                block_id_match = re.search(r'P\d{2,4}\.(\d{4})', content)
                if block_id_match:
                    name_match = re.search(r'(P\d{2,4}\.\d{4}\s*/[A-Z]+)', content)
                    name = name_match.group(1).replace(" ", "") if name_match else content.split('\\')[0].replace(" ", "").replace(";", "").replace("{", "")
                    
                    num_id = str(int(block_id_match.group(1)))
                    lbs_info.append({
                        'name': name,
                        'id': num_id,
                        'insert': insert_pt,
                        'raw_text': raw_content,
                        'layout_name': layout_name
                    })
            
            if 'C' in content or 'H' in content or 'SP' in content or '-' in content:
                lspls_texts.append({
                    'text': raw_content,
                    'insert': insert_pt
                })
                
            val_upper = content.upper()
            is_attr = (
                'SP' in val_upper or '1:' in val_upper or '2X' in val_upper or
                any(val_upper.startswith(x) for x in ['H', 'C', 'M', 'T', 'O', 'B', 'F', 'D']) or
                re.search(r'\d+:\d+', val_upper)
            )
            if is_attr:
                lattrs_texts.append({
                    'text': raw_content,
                    'insert': insert_pt
                })
                
        return lbs_info, llns_pts, lspls_texts, lattrs_texts

    # Extract blocks, lines, splices, attributes from the selected layouts
    blocks_info = []
    lines_pts = []
    splices_texts = []
    attributes_texts = []
    
    for l in layouts:
        lbs, llns, lspls, lattrs = process_layout(l, getattr(l, 'name', 'Model'))
        blocks_info.extend(lbs)
        lines_pts.extend(llns)
        splices_texts.extend(lspls)
        attributes_texts.extend(lattrs)

    # Build topological connectivity graph using active layout data
    unique_pts = []
    for p1, p2 in lines_pts:
        unique_pts.append(p1)
        unique_pts.append(p2)
        
    parent_map = {}
    spatial_grid = {}
    grid_size = 5.0
    
    def get_grid_cells(pt):
        cx = int(pt.x / grid_size)
        cy = int(pt.y / grid_size)
        return [(cx + dx, cy + dy) for dx in [-1, 0, 1] for dy in [-1, 0, 1]]
        
    def find_rep(pt):
        cells = get_grid_cells(pt)
        for cell in cells:
            if cell in spatial_grid:
                for rep in spatial_grid[cell]:
                    if rep.distance(pt) < 5.0:
                        return rep
        parent_map[pt] = pt
        cx = int(pt.x / grid_size)
        cy = int(pt.y / grid_size)
        spatial_grid.setdefault((cx, cy), []).append(pt)
        return pt
        
    for pt in unique_pts:
        find_rep(pt)
        
    graph = {}
    for p1, p2 in lines_pts:
        r1 = find_rep(p1)
        r2 = find_rep(p2)
        if r1 != r2:
            graph.setdefault(r1, []).append(r2)
            graph.setdefault(r2, []).append(r1)
            
    # Map active cabinets to closest graph vertices
    cabinet_vertices = {}
    vertex_to_cabinet = {}
    for b in blocks_info:
        closest_v = None
        min_d = float('inf')
        b_pt = b['insert']
        
        # Spatial Grid search for closest welded vertex (max dist 80.0)
        cx = int(b_pt.x / grid_size)
        cy = int(b_pt.y / grid_size)
        search_radius = 17 # 17 * 5.0 = 85.0 units search window
        for dx in range(-search_radius, search_radius + 1):
            for dy in range(-search_radius, search_radius + 1):
                cell = (cx + dx, cy + dy)
                if cell in spatial_grid:
                    for v in spatial_grid[cell]:
                        dist = v.distance(b_pt)
                        if dist < min_d:
                            min_d = dist
                            closest_v = v
                            
        if min_d < 80.0 and closest_v is not None:
            rep_v = find_rep(closest_v)
            cabinet_vertices[b['name']] = rep_v
            vertex_to_cabinet[rep_v] = b['name']
            
    # Trace BFS from each cabinet to find direct physical path connections
    edges = []
    from collections import deque
    for b_name, start_v in cabinet_vertices.items():
        b_info = next(x for x in blocks_info if x['name'] == b_name)
        queue = deque([start_v])
        visited = {start_v}
        
        while queue:
            curr = queue.popleft()
            if curr in vertex_to_cabinet and curr != start_v:
                other_name = vertex_to_cabinet[curr]
                other_info = next(x for x in blocks_info if x['name'] == other_name)
                
                # Flow from left (smaller X) to right (larger X) for backwards compatibility
                if b_info['insert'].x < other_info['insert'].x:
                    edges.append((b_name, other_name))
                else:
                    edges.append((other_name, b_name))
                continue
                
            for neighbor in graph.get(curr, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
                    
    # Deduplicate edges
    edges = list(set(edges))
    
    # Store physical parent options
    model_geom_parents = {}
    for b in blocks_info:
        b_name = b['name']
        geom_parents_list = []
        for e in edges:
            if e[1] == b_name:
                geom_parents_list.append(e[0])
        model_geom_parents[b_name] = geom_parents_list

    def count_underlined(block_insert, target_id, text_list):
        target_id_int = str(int(target_id))
        name_pattern = rf"^C0*{target_id_int}(?!\d)"
        
        has_sp1_near = any((txt['insert'] - block_insert).magnitude < 20.0 and 'SP1' in strip_formatting(txt['text']) for txt in text_list)
        has_sp2_near = any((txt['insert'] - block_insert).magnitude < 20.0 and 'SP2' in strip_formatting(txt['text']) for txt in text_list)
        
        candidates = []
        for item in text_list:
            dist = (item['insert'] - block_insert).magnitude
            if dist < 100.0 and '-' in strip_formatting(item['text']):
                text = item['text']
                first_line = re.split(r'\\P|\n|\^J', text)[0]
                first_line_clean = strip_formatting(first_line)
                
                is_sp_candidate = False
                if dist < 50.0:
                    if (first_line_clean.startswith('SP1') or first_line_clean.startswith('1.SP')) and has_sp1_near:
                        is_sp_candidate = True
                    elif (first_line_clean.startswith('SP2') or first_line_clean.startswith('2.SP')) and has_sp2_near:
                        is_sp_candidate = True
                
                is_name_match = bool(re.match(name_pattern, first_line_clean)) or is_sp_candidate
                
                # Count underlined in this specific text block
                splices_keys = set()
                lines = re.split(r'\\P|\n|\^J', text)
                in_underline = False
                for line in lines:
                    if '-' in line:
                        left_part = line.split('-')[0]
                        codes = []
                        for m in re.finditer(r'\\[L|l]|}', left_part):
                            codes.append((m.start(), m.group()))
                        
                        if codes:
                            last_code = codes[-1][1]
                            in_underline_at_hyphen = (last_code == '\\L')
                        else:
                            in_underline_at_hyphen = in_underline
                        
                        if in_underline_at_hyphen:
                            core_keys = parse_connection_cores(line)
                            splices_keys.update(core_keys)
                    
                    all_codes = []
                    for m in re.finditer(r'\\[L|l]|}', line):
                        all_codes.append((m.start(), m.group()))
                    if all_codes:
                        last_code = all_codes[-1][1]
                        in_underline = (last_code == '\\L')
                
                splices_count = len(splices_keys)
                if is_name_match and splices_count > 0:
                    priority = 1
                elif is_name_match and splices_count == 0:
                    priority = 2
                elif not is_name_match and splices_count > 0:
                    priority = 3
                else:
                    priority = 4
                    
                candidates.append({
                    'dist': dist,
                    'splices_keys': splices_keys,
                    'splices': splices_count,
                    'priority': priority
                })
                
        p1 = [c for c in candidates if c['priority'] == 1]
        p2 = [c for c in candidates if c['priority'] == 2]
        p3 = [c for c in candidates if c['priority'] == 3]
        
        if p1:
            p1_close = [c for c in p1 if c['dist'] < 50.0]
            if p1_close:
                union_keys = set()
                for c in p1_close:
                    union_keys.update(c['splices_keys'])
                return union_keys
            else:
                p1.sort(key=lambda x: x['dist'])
                return p1[0]['splices_keys']
        elif p2:
            return set()
        elif p3:
            p3.sort(key=lambda x: x['dist'])
            if p3[0]['dist'] < 50.0:
                return p3[0]['splices_keys']
            else:
                return set()
        else:
            return set()

    # Build explicit links from text formatting
    explicit_links = []
    for item in splices_texts:
        clean_text = strip_formatting(item['text'])
        
        owner_id = None
        owner_match = re.search(r'\b[CHFTM]0*(\d{1,4})\b\.\d+\s*-\s*\d*\.?SP', clean_text)
        if owner_match:
            owner_id = str(int(owner_match.group(1)))
        else:
            first_line = re.split(r'\\P|\n|\^J', clean_text)[0]
            owner_match_2 = re.search(r'\b[CHFTM]0*(\d{1,4})\b', first_line)
            if owner_match_2:
                owner_id = str(int(owner_match_2.group(1)))
                
        for line in re.split(r'\\P|\n|\^J', clean_text):
            if '-' in line:
                parts = line.split('-')
                if len(parts) >= 2:
                    left_part = parts[0]
                    right_part = parts[1]
                    
                    pid = None
                    cid = None
                    
                    right_match = re.search(r'\b[CHFTM]0*(\d{1,4})\b', right_part)
                    if right_match:
                        cid = str(int(right_match.group(1)))
                        
                    left_match = re.search(r'\b[CHFTM]0*(\d{1,4})\b', left_part)
                    if left_match:
                        pid = str(int(left_match.group(1)))
                    elif 'SP' in left_part and owner_id:
                        pid = owner_id
                        
                    if pid and cid and pid != cid:
                        explicit_links.append((pid, cid, item['insert']))

    explicit_parents = {}
    for b in blocks_info:
        target_num_id = b['id']
        child_links = [link for link in explicit_links if link[1] == target_num_id]
        if child_links:
            # Sort by distance to child block to ensure it's the text meant for this child
            child_links.sort(key=lambda x: (x[2] - b['insert']).magnitude)
            best_pid = child_links[0][0]
            parent_blocks = [pb for pb in blocks_info if pb['id'] == best_pid]
            if parent_blocks:
                parent_blocks.sort(key=lambda x: (child_links[0][2] - x['insert']).magnitude)
                explicit_parents[b['name']] = parent_blocks[0]['name']

    unique_keys_by_id = {}
    for b in blocks_info:
        cab_id = b['id']
        if cab_id not in unique_keys_by_id:
            unique_keys_by_id[cab_id] = set()
        block_keys = count_underlined(b['insert'], cab_id, splices_texts)
        unique_keys_by_id[cab_id].update(block_keys)

    def find_nearby_attributes(insert_pt, lattrs, max_dist=15.0):
        box_code = ""
        capacity_text = ""
        closest_box_dist = float('inf')
        closest_cap_dist = float('inf')
        
        for t in lattrs:
            t_pt = t['insert']
            dist = insert_pt.distance(t_pt)
            if dist <= max_dist:
                val = strip_formatting(t['text']).strip()
                if val.startswith('P') or val.startswith('p'):
                    if len(val) > 1 and val[1].upper() in ['C', 'H', 'S', 'M', 'T', 'O', 'B', 'F', 'D', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
                        val = val[1:]
                
                val_clean = val.upper().strip()
                # Skip cable labels: e.g. "C234 12 core", "12 core", "C234", etc.
                if 'CORE' in val_clean or re.match(r'^C\d+', val_clean):
                    continue
                        
                if 'SP' in val.upper() or '1:' in val.upper() or '2X' in val.upper() or 'CAP' in val.upper() or ':' in val:
                    if dist < closest_cap_dist:
                        closest_cap_dist = dist
                        capacity_text = val
                elif any(val.upper().startswith(x) for x in ['H', 'C', 'M', 'T', 'O', 'B', 'F', 'D']):
                    if dist < closest_box_dist:
                        closest_box_dist = dist
                        box_code = val
                else:
                    if not box_code and dist < closest_box_dist:
                        closest_box_dist = dist
                        box_code = val
                        
        return box_code, capacity_text

    results = {}
    for b in blocks_info:
        name = b['name']
        cab_id = b['id']
        
        # 1. Text-based parent
        diem_dau = "Không tìm thấy"
        if name in explicit_parents:
            diem_dau = explicit_parents[name]
            
        # 2. Physics-based parent (geom_parent) with Smart Best-Match sorting!
        geom_parents_list = model_geom_parents.get(name, [])
        geom_parent = "Không tìm thấy"
        conflict = False
        
        if geom_parents_list:
            # Smart Best-Match: prioritize the physical parent that matches text parent's prefix/id!
            p_dau_short = diem_dau.split('/')[0] if '/' in diem_dau else diem_dau
            best_gp = None
            for gp in geom_parents_list:
                gp_short = gp.split('/')[0] if '/' in gp else gp
                if gp_short == p_dau_short:
                    best_gp = gp
                    break
            
            if best_gp:
                geom_parent = best_gp
                # Fully consistent! conflict = False
            else:
                geom_parents_list.sort(key=lambda x: 0 if '/' in x else 1)
                geom_parent = geom_parents_list[0]
                # ONLY mark line conflict warning if the cabinet is drawn in ModelSpace (true geographic map)
                layout_name = b.get('layout_name', 'Model')
                if diem_dau != "Không tìm thấy" and layout_name.upper() == 'MODEL':
                    conflict = True
        else:
            if diem_dau == "Không tìm thấy":
                # No text parent and no physical parent
                pass
            
        so_moi_han = len(unique_keys_by_id.get(cab_id, set()))
        
        raw_text = b.get('raw_text', '')
        box_code, cap_text = parse_block_attrs(raw_text)
        
        # Spatial Proximity Fallback: If attributes not embedded in cabinet text, search nearby
        if not box_code or not cap_text:
            near_box, near_cap = find_nearby_attributes(b['insert'], attributes_texts, max_dist=15.0)
            if not box_code:
                box_code = near_box
            if not cap_text:
                cap_text = near_cap
                
        capacity_disp = format_cad_capacity_display(cap_text)

        val_data = {
            'parent': diem_dau,
            'geom_parent': geom_parent,
            'splices': so_moi_han,
            'conflict': conflict,
            'box_code': box_code,
            'capacity_text': capacity_disp
        }

        # Store under the original name
        results[name] = val_data
        
        # Store under the short key (e.g. HNIP473.0234)
        short_key = name.split('/')[0] if '/' in name else name
        results[short_key] = val_data
        
        # Also store under 'P' sliced versions (e.g. P473.0234/HO and P473.0234)
        p_idx = name.upper().find('P')
        if p_idx != -1:
            p_name = name[p_idx:]
            results[p_name] = val_data
            p_short = p_name.split('/')[0] if '/' in p_name else p_name
            results[p_short] = val_data
            
    return results
