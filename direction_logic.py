import numpy as np

class DirectionTracker:
    def __init__(self, line_coords, top_line_coords=None):
        """
        line_coords: ((x1, y1), (x2, y2)) defining the main gate
        top_line_coords: ((x1, y1), (x2, y2)) defining the secondary top gate
        """
        self.p1 = np.array(line_coords[0])
        self.p2 = np.array(line_coords[1])
        
        self.has_top_line = top_line_coords is not None
        if self.has_top_line:
            self.tp1 = np.array(top_line_coords[0])
            self.tp2 = np.array(top_line_coords[1])
            
        self.track_history = {} # {id: last_pos}
        self.violators = set() # Store IDs of vehicles that violated

    def get_side(self, point, p1, p2):
        """
        Determines which side of the line a point is on using cross product.
        Returns > 0 for one side, < 0 for the other.
        """
        return (p2[0] - p1[0]) * (point[1] - p1[1]) - \
               (p2[1] - p1[1]) * (point[0] - p1[0])

    def update(self, object_id, centroid):
        """
        Returns: 'correct', 'new_violation', 'already_violator', or None
        """
        if object_id not in self.track_history:
            self.track_history[object_id] = centroid
            if object_id in self.violators:
                return 'already_violator'
            return None

        prev_pos = self.track_history[object_id]
        self.track_history[object_id] = centroid
        
        if object_id in self.violators:
            return 'already_violator'

        # Check main line
        prev_side = self.get_side(prev_pos, self.p1, self.p2)
        curr_side = self.get_side(centroid, self.p1, self.p2)

        is_violation = False
        # If moving from below (> 0) to above (< 0), it's moving UP (violation)
        if prev_side > 0 and curr_side < 0:
            is_violation = True
            
        # Check top line if no violation yet on main line
        if not is_violation and self.has_top_line:
            prev_top_side = self.get_side(prev_pos, self.tp1, self.tp2)
            curr_top_side = self.get_side(centroid, self.tp1, self.tp2)
            if prev_top_side > 0 and curr_top_side < 0:
                is_violation = True

        if is_violation:
            self.violators.add(object_id)
            return 'new_violation'
            
        if prev_side < 0 and curr_side > 0:
            return 'correct'
            
        return None
