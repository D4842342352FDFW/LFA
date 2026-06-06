from collections import deque

def all_simple_paths(neighbors_fn, start_id, end_id, max_extra=1, max_paths=24):

    sp = bfs_path(neighbors_fn, start_id, end_id)
    if not sp:
        return []
    max_len = len(sp) + max_extra
    paths = []

    def dfs(path, visited):
        if len(paths) >= max_paths:
            return
        curr = path[-1]
        if curr == end_id:
            paths.append(list(path))
            return
        if len(path) >= max_len:
            return
        for nb in neighbors_fn(curr):
            if nb not in visited:
                visited.add(nb)
                path.append(nb)
                dfs(path, visited)
                path.pop()
                visited.discard(nb)

    dfs([start_id], {start_id})
    return paths

def bfs_path(neighbors_fn, start_id, end_id):

    if start_id == end_id:
        return [start_id]
    prev = {start_id: None}
    q = deque([start_id])
    while q:
        nid = q.popleft()
        for nb in neighbors_fn(nid):
            if nb not in prev:
                prev[nb] = nid
                if nb == end_id:
                    path, cur = [], end_id
                    while cur is not None:
                        path.append(cur)
                        cur = prev[cur]
                    path.reverse()
                    return path
                q.append(nb)
    return []

def all_shortest_paths(neighbors_fn, start_id, end_id, max_paths=10):

    if start_id == end_id:
        return [[start_id]]
    dist_s = {start_id: 0}
    q = deque([start_id])
    while q:
        nid = q.popleft()
        for nb in neighbors_fn(nid):
            if nb not in dist_s:
                dist_s[nb] = dist_s[nid] + 1
                q.append(nb)
    if end_id not in dist_s:
        return []
    dist_e = {end_id: 0}
    q = deque([end_id])
    while q:
        nid = q.popleft()
        for nb in neighbors_fn(nid):
            if nb not in dist_e:
                dist_e[nb] = dist_e[nid] + 1
                q.append(nb)
    shortest_len = dist_s[end_id]
    all_paths = []

    def dfs(path, visited):
        if len(all_paths) >= max_paths:
            return
        curr = path[-1]
        if curr == end_id:
            all_paths.append(list(path))
            return
        d = dist_s[curr]
        if d >= shortest_len:
            return
        for nb in neighbors_fn(curr):
            if nb in visited:
                continue
            if (dist_s.get(nb, -1) == d + 1 and
                    dist_s.get(nb, 0) + dist_e.get(nb, float('inf')) == shortest_len):
                visited.add(nb)
                path.append(nb)
                dfs(path, visited)
                path.pop()
                visited.discard(nb)

    dfs([start_id], {start_id})
    return all_paths
