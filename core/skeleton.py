"""
Skeleton module for character rigging and pose management
"""

import json
import math
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from copy import deepcopy
import uuid


class JointRole(Enum):
    """Role of a joint in the skeleton"""
    ROOT = "root"
    HIP = "hip"
    SPINE = "spine"
    CHEST = "chest"
    NECK = "neck"
    HEAD = "head"
    HEADTOP = "headtop"
    SHOULDER = "shoulder"
    ELBOW = "elbow"
    WRIST = "wrist"
    HAND = "hand"
    KNEE = "knee"
    ANKLE = "ankle"
    TOE = "toe"
    ARM = "arm"
    LEG = "leg"
    FOOT = "foot"
    PELVIS = "pelvis"
    OTHER = "other"


class JointSide(Enum):
    """Side of a joint (left, right, center)"""
    LEFT = "L"
    RIGHT = "R"
    CENTER = "C"


@dataclass
class Joint:
    """Represents a joint in the skeleton"""
    id: str
    name: str
    role: JointRole
    parent_id: Optional[str]
    pair_id: Optional[str]  # ID of mirrored joint
    x: float  # 2D position in canvas coordinates
    y: float
    nx: float = 0.0  # Normalized X position (0-1)
    ny: float = 0.0  # Normalized Y position (0-1)
    local_position: Tuple[float, float, float] = (0, 0, 0)  # 3D local position
    world_position: Tuple[float, float, float] = (0, 0, 0)  # 3D world position
    radius_x: float = 0.0  # Radius for capsule
    radius_z: float = 0.0
    
    def get_side(self) -> JointSide:
        """Determine joint side from name"""
        if '_L' in self.name or self.name.endswith('_L'):
            return JointSide.LEFT
        elif '_R' in self.name or self.name.endswith('_R'):
            return JointSide.RIGHT
        return JointSide.CENTER
    
    def is_left(self) -> bool:
        return self.get_side() == JointSide.LEFT
    
    def is_right(self) -> bool:
        return self.get_side() == JointSide.RIGHT
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'role': self.role.value,
            'parent': self.parent_id,
            'pair': self.pair_id,
            'x': self.x,
            'y': self.y,
            'nx': self.nx,
            'ny': self.ny
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Joint':
        """Create joint from dictionary"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', 'Joint'),
            role=JointRole(data.get('role', 'other')),
            parent_id=data.get('parent'),
            pair_id=data.get('pair'),
            x=data.get('x', 0),
            y=data.get('y', 0),
            nx=data.get('nx', 0),
            ny=data.get('ny', 0)
        )


@dataclass
class Bone:
    """Represents a bone connecting two joints"""
    name: str
    from_joint_id: str
    to_joint_id: str
    region: str  # Body region (e.g., 'arm', 'leg', 'torso')
    length_cm: float = 0.0
    capsule_radius_x: float = 0.0
    capsule_radius_z: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'from': self.from_joint_id,
            'to': self.to_joint_id,
            'region': self.region,
            'lengthCm': self.length_cm,
            'capsule': {
                'radiusXCm': self.capsule_radius_x,
                'radiusZCm': self.capsule_radius_z
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Bone':
        capsule = data.get('capsule', {})
        return cls(
            name=data.get('name', 'Bone'),
            from_joint_id=data.get('from', ''),
            to_joint_id=data.get('to', ''),
            region=data.get('region', 'other'),
            length_cm=data.get('lengthCm', 0),
            capsule_radius_x=capsule.get('radiusXCm', 0),
            capsule_radius_z=capsule.get('radiusZCm', 0)
        )


@dataclass
class ContourPoint:
    """Point in a body contour"""
    x: float
    y: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {'x': self.x, 'y': self.y}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContourPoint':
        return cls(x=data.get('x', 0), y=data.get('y', 0))


@dataclass
class BodyContour:
    """Represents a body contour for defining segment thickness"""
    id: str
    name: str
    points: List[ContourPoint] = field(default_factory=list)
    joint_id: Optional[str] = None  # Associated joint
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'points': [p.to_dict() for p in self.points],
            'jointId': self.joint_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BodyContour':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', 'Contour'),
            points=[ContourPoint.from_dict(p) for p in data.get('points', [])],
            joint_id=data.get('jointId')
        )


class Skeleton:
    """
    Main skeleton class for managing character rigging
    """
    
    def __init__(self):
        self.joints: Dict[str, Joint] = {}
        self.bones: List[Bone] = []
        self.contours: List[BodyContour] = []
        self.parameters: Dict[str, Any] = {
            'target_height_cm': 180,
            'chest_depth_cm': 40,
            'pelvis_depth_cm': 25,
            'limb_bend_cm': 4,
            'capsule_radii_cm': {
                'torso': 15,
                'arms': 6,
                'legs': 9
            },
            'toe_forward_cm': 10,
            'auto_radius': True,
            'mirror_symmetry': True,
            'natural_height_u': 180.0,
            'applied_scale': 1.0,
            'floor_by_joint': 'Toe_L',
            'floor_mode': 'foot',
            'top_by_joint': 'HeadTop',
            'top_mode': 'headtop'
        }
        self._next_id: int = 1
        self._history: List[Dict[str, Any]] = []
        self._history_index: int = -1
    
    def add_joint(self, joint: Joint) -> None:
        """Add a joint to the skeleton"""
        self.joints[joint.id] = joint
        self._next_id = max(self._next_id, int(joint.id.replace('j', '')) + 1) if joint.id.startswith('j') else self._next_id + 1
    
    def remove_joint(self, joint_id: str) -> bool:
        """Remove a joint from the skeleton"""
        if joint_id not in self.joints:
            return False
        
        joint = self.joints[joint_id]
        
        # Remove from parent's children
        for j in self.joints.values():
            if j.parent_id == joint_id:
                j.parent_id = None
        
        # Remove bones connected to this joint
        self.bones = [b for b in self.bones if b.from_joint_id != joint_id and b.to_joint_id != joint_id]
        
        # Remove contours associated with this joint
        self.contours = [c for c in self.contours if c.joint_id != joint_id]
        
        del self.joints[joint_id]
        return True
    
    def get_joint(self, joint_id: str) -> Optional[Joint]:
        """Get a joint by ID"""
        return self.joints.get(joint_id)
    
    def get_root_joints(self) -> List[Joint]:
        """Get all root joints (joints without parents)"""
        return [j for j in self.joints.values() if j.parent_id is None]
    
    def get_children(self, joint_id: str) -> List[Joint]:
        """Get all children of a joint"""
        return [j for j in self.joints.values() if j.parent_id == joint_id]
    
    def get_paired_joint(self, joint_id: str) -> Optional[Joint]:
        """Get the mirrored pair of a joint"""
        joint = self.joints.get(joint_id)
        if joint and joint.pair_id:
            return self.joints.get(joint.pair_id)
        return None
    
    def create_mirrored_joint(self, source_id: str, side: JointSide) -> Optional[Joint]:
        """Create a mirrored version of a joint"""
        source = self.joints.get(source_id)
        if not source:
            return None
        
        # Determine target side
        if side == JointSide.LEFT:
            target_side = JointSide.RIGHT
        elif side == JointSide.RIGHT:
            target_side = JointSide.LEFT
        else:
            return None
        
        # Create mirrored name
        target_name = source.name.replace('_L', '_R') if '_L' in source.name else \
                      source.name.replace('_R', '_L') if '_R' in source.name else \
                      source.name + '_' + target_side.value
        
        # Mirror X coordinate
        target_x = -source.x
        
        new_joint = Joint(
            id=str(uuid.uuid4()),
            name=target_name,
            role=source.role,
            parent_id=source.parent_id,  # Will need to be updated
            pair_id=source.id,
            x=target_x,
            y=source.y,
            nx=-source.nx,
            ny=source.ny
        )
        
        # Update pair reference
        source.pair_id = new_joint.id
        
        return new_joint
    
    def add_bone(self, bone: Bone) -> None:
        """Add a bone to the skeleton"""
        self.bones.append(bone)
    
    def remove_bone(self, bone_name: str) -> bool:
        """Remove a bone by name"""
        for i, bone in enumerate(self.bones):
            if bone.name == bone_name:
                self.bones.pop(i)
                return True
        return False
    
    def get_bones_from_joint(self, joint_id: str) -> List[Bone]:
        """Get all bones connected to a joint"""
        return [b for b in self.bones if b.from_joint_id == joint_id or b.to_joint_id == joint_id]
    
    def add_contour(self, contour: BodyContour) -> None:
        """Add a body contour"""
        self.contours.append(contour)
    
    def remove_contour(self, contour_id: str) -> bool:
        """Remove a contour by ID"""
        for i, contour in enumerate(self.contours):
            if contour.id == contour_id:
                self.contours.pop(i)
                return True
        return False
    
    def generate_bones(self) -> None:
        """Generate bones from joint hierarchy"""
        self.bones = []
        
        for joint in self.joints.values():
            if joint.parent_id and joint.parent_id in self.joints:
                parent = self.joints[joint.parent_id]
                bone_name = f"{parent.name}___{joint.name}"
                
                # Determine region
                region = self._get_bone_region(parent, joint)
                
                # Calculate length (in 2D for now)
                length = math.sqrt((joint.x - parent.x)**2 + (joint.y - parent.y)**2)
                
                bone = Bone(
                    name=bone_name,
                    from_joint_id=parent.id,
                    to_joint_id=joint.id,
                    region=region,
                    length_cm=length,
                    capsule_radius_x=0,
                    capsule_radius_z=0
                )
                self.bones.append(bone)
    
    def _get_bone_region(self, parent: Joint, child: Joint) -> str:
        """Determine bone region based on joint roles"""
        parent_role = parent.role.value
        child_role = child.role.value
        
        # Common regions
        if 'spine' in parent_role or 'pelvis' in parent_role:
            if 'spine' in child_role:
                return 'pelvis'
            elif 'chest' in child_role:
                return 'belly'
        elif 'chest' in parent_role:
            if 'neck' in child_role:
                return 'chest'
            elif 'shoulder' in child_role:
                return 'shoulder'
        elif 'shoulder' in parent_role:
            if 'elbow' in child_role:
                return 'arm'
        elif 'elbow' in parent_role:
            if 'wrist' in child_role:
                return 'hand'
        elif 'hip' in parent_role:
            if 'knee' in child_role:
                return 'thigh'
        elif 'knee' in parent_role:
            if 'ankle' in child_role:
                return 'shin'
        elif 'ankle' in parent_role:
            if 'toe' in child_role:
                return 'foot'
        
        return 'other'
    
    def _get_center_x(self) -> float:
        """Get the center X coordinate of all joints"""
        if not self.joints:
            return 0.0
        xs = [j.x for j in self.joints.values()]
        return sum(xs) / len(xs)
    
    def calculate_world_positions(self, scale: float = 1.0) -> None:
        """
        Calculate world positions for all joints from 2D canvas coordinates
        
        According to the format:
        - X=0 is center
        - Y=0 is floor
        - Character faces +Z
        - L=+X (left is positive X)
        - nx = x / natural_height
        - ny = (y - floor) / natural_height
        
        Args:
            scale: Scale factor to convert 2D coordinates to 3D (meters)
        """
        # Get parameters
        natural_height = self.parameters.get('natural_height_u', 180.0)
        
        # Calculate floor height in 2D coordinates
        floor_y = self.calculate_floor_height()
        
        # Convert all joints to 3D
        for joint in self.joints.values():
            # Convert 2D canvas coordinates to 3D world coordinates
            # X axis: canvas X -> world X (L=+X)
            # Y axis: canvas Y -> world Z (up)
            # Z axis: canvas depth -> world Y (forward/backward, but we use 0 for now)
            
            # Scale factor from normalized coordinates
            if natural_height > 0:
                # If nx, ny are available, use them
                if joint.nx != 0 or joint.ny != 0:
                    world_x = joint.nx * scale
                    world_z = joint.ny * scale
                else:
                    # Use x, y coordinates directly
                    world_x = (joint.x / natural_height) * scale
                    world_z = ((joint.y - floor_y) / natural_height) * scale
            else:
                world_x = joint.x * scale / 100.0  # Assume x is in pixels, convert to meters
                world_z = (joint.y - floor_y) * scale / 100.0
            
            # Y coordinate is always 0 (on the floor) for 2D joints
            # In 3D space, we'll use:
            # - X: left-right (L=+X)
            # - Y: depth (forward/backward from camera)
            # - Z: height (up-down)
            # But for simplicity, we'll use:
            # - X: left-right
            # - Y: height (up-down)
            # - Z: depth (forward/backward)
            
            # Actually, let's use standard convention:
            # - X: left-right (L=+X)
            # - Y: up-down
            # - Z: forward-backward
            # But character faces +Z, so we need to adjust
            
            # From the JSON notes: "персонаж смотрит +Z"
            # So +Z is forward (facing direction)
            # +X is left
            # +Y is up
            
            # In 2D canvas:
            # - x: left-right (0 is center, -x is right, +x is left)
            # - y: up-down (0 is floor, +y is up)
            
            # Wait, let's reconsider based on the JSON:
            # "ось X=0 — центр; пол Y=0 по стопам"
            # So in 2D: X=0 is center, Y=0 is floor
            # "персонаж смотрит +Z; L=+X"
            # So in 3D: +Z is forward, +X is left
            
            # Converting 2D to 3D:
            # - 2D x (left-right) -> 3D X (left is positive)
            # - 2D y (up-down from floor) -> 3D Y (height)
            # - 2D depth (not present in 2D) -> 3D Z (forward, default 0)
            
            world_y = 0.0  # All joints start on the floor
            world_z = 0.0  # No depth in 2D
            
            # But we need height! The y coordinate in 2D is the height from floor
            # So we should use y as the Y coordinate (height)
            
            # Let's use:
            # - X: x coordinate (left-right), with center at 0
            # - Y: y coordinate (height from floor)
            # - Z: 0 (no depth)
            
            # But we need to convert from canvas coordinates to world coordinates
            # Canvas: x=0 is center, y=0 is floor
            # World: X=0 is center, Y=0 is floor, Z=0 is origin
            
            # Scale down from canvas coordinates
            # Assuming canvas coordinates are in pixels
            # We want meters: 180 cm = 1.8 m
            
            # Simple conversion:
            world_x = (joint.x - self._get_center_x()) * scale / 100.0
            world_y = (joint.y - floor_y) * scale / 100.0
            world_z = 0.0
            
            joint.world_position = (float(world_x), float(world_y), float(world_z))
            joint.local_position = joint.world_position
    
    def calculate_floor_height(self) -> float:
        """Calculate floor height based on foot joints"""
        floor_joint_name = self.parameters.get('floor_by_joint', 'Toe_L')
        floor_mode = self.parameters.get('floor_mode', 'foot')
        
        floor_joint = None
        for joint in self.joints.values():
            if joint.name == floor_joint_name:
                floor_joint = joint
                break
        
        if floor_joint:
            return floor_joint.y
        
        # Fallback: find lowest joint
        min_y = float('inf')
        for joint in self.joints.values():
            if joint.y < min_y:
                min_y = joint.y
        
        return min_y
    
    def calculate_height(self) -> float:
        """Calculate total height of the skeleton"""
        top_joint_name = self.parameters.get('top_by_joint', 'HeadTop')
        floor_height = self.calculate_floor_height()
        
        top_joint = None
        for joint in self.joints.values():
            if joint.name == top_joint_name:
                top_joint = joint
                break
        
        if top_joint:
            return top_joint.y - floor_height
        
        # Fallback: find highest joint
        max_y = float('-inf')
        for joint in self.joints.values():
            if joint.y > max_y:
                max_y = joint.y
        
        return max_y - floor_height
    
    def apply_mirror_symmetry(self) -> None:
        """Apply mirror symmetry to the skeleton"""
        if not self.parameters.get('mirror_symmetry', True):
            return
        
        # Find all left joints without right counterparts
        for joint in self.joints.values():
            if joint.is_left() and not joint.pair_id:
                mirrored = self.create_mirrored_joint(joint.id, JointSide.LEFT)
                if mirrored:
                    self.add_joint(mirrored)
            elif joint.is_right() and not joint.pair_id:
                mirrored = self.create_mirrored_joint(joint.id, JointSide.RIGHT)
                if mirrored:
                    self.add_joint(mirrored)
    
    def create_preset_t_pose(self) -> None:
        """Create a T-pose preset skeleton"""
        self.clear()
        
        # Create joints for T-pose
        center_x = 0
        
        # Pelvis
        pelvis = Joint(
            id='j1',
            name='Pelvis',
            role=JointRole.ROOT,
            parent_id=None,
            pair_id=None,
            x=center_x,
            y=100,
            nx=0,
            ny=0.5
        )
        self.add_joint(pelvis)
        
        # Spine
        spine = Joint(
            id='j2',
            name='Spine',
            role=JointRole.SPINE,
            parent_id='j1',
            pair_id=None,
            x=center_x,
            y=120,
            nx=0,
            ny=0.6
        )
        self.add_joint(spine)
        
        # Chest
        chest = Joint(
            id='j3',
            name='Chest',
            role=JointRole.CHEST,
            parent_id='j2',
            pair_id=None,
            x=center_x,
            y=140,
            nx=0,
            ny=0.7
        )
        self.add_joint(chest)
        
        # Neck
        neck = Joint(
            id='j4',
            name='Neck',
            role=JointRole.NECK,
            parent_id='j3',
            pair_id=None,
            x=center_x,
            y=160,
            nx=0,
            ny=0.8
        )
        self.add_joint(neck)
        
        # Head
        head = Joint(
            id='j5',
            name='Head',
            role=JointRole.HEAD,
            parent_id='j4',
            pair_id=None,
            x=center_x,
            y=175,
            nx=0,
            ny=0.9
        )
        self.add_joint(head)
        
        # HeadTop
        headtop = Joint(
            id='j6',
            name='HeadTop',
            role=JointRole.HEADTOP,
            parent_id='j5',
            pair_id=None,
            x=center_x,
            y=185,
            nx=0,
            ny=1.0
        )
        self.add_joint(headtop)
        
        # Shoulders
        shoulder_l = Joint(
            id='j7',
            name='Shoulder_L',
            role=JointRole.SHOULDER,
            parent_id='j3',
            pair_id='j10',
            x=center_x - 25,
            y=145,
            nx=-0.15,
            ny=0.8
        )
        self.add_joint(shoulder_l)
        
        shoulder_r = Joint(
            id='j10',
            name='Shoulder_R',
            role=JointRole.SHOULDER,
            parent_id='j3',
            pair_id='j7',
            x=center_x + 25,
            y=145,
            nx=0.15,
            ny=0.8
        )
        self.add_joint(shoulder_r)
        
        # Elbows
        elbow_l = Joint(
            id='j8',
            name='Elbow_L',
            role=JointRole.ELBOW,
            parent_id='j7',
            pair_id='j11',
            x=center_x - 50,
            y=140,
            nx=-0.3,
            ny=0.75
        )
        self.add_joint(elbow_l)
        
        elbow_r = Joint(
            id='j11',
            name='Elbow_R',
            role=JointRole.ELBOW,
            parent_id='j10',
            pair_id='j8',
            x=center_x + 50,
            y=140,
            nx=0.3,
            ny=0.75
        )
        self.add_joint(elbow_r)
        
        # Wrists
        wrist_l = Joint(
            id='j9',
            name='Wrist_L',
            role=JointRole.WRIST,
            parent_id='j8',
            pair_id='j12',
            x=center_x - 75,
            y=135,
            nx=-0.45,
            ny=0.7
        )
        self.add_joint(wrist_l)
        
        wrist_r = Joint(
            id='j12',
            name='Wrist_R',
            role=JointRole.WRIST,
            parent_id='j11',
            pair_id='j9',
            x=center_x + 75,
            y=135,
            nx=0.45,
            ny=0.7
        )
        self.add_joint(wrist_r)
        
        # Hips
        hip_l = Joint(
            id='j13',
            name='Hip_L',
            role=JointRole.HIP,
            parent_id='j1',
            pair_id='j16',
            x=center_x - 10,
            y=90,
            nx=-0.05,
            ny=0.5
        )
        self.add_joint(hip_l)
        
        hip_r = Joint(
            id='j16',
            name='Hip_R',
            role=JointRole.HIP,
            parent_id='j1',
            pair_id='j13',
            x=center_x + 10,
            y=90,
            nx=0.05,
            ny=0.5
        )
        self.add_joint(hip_r)
        
        # Knees
        knee_l = Joint(
            id='j14',
            name='Knee_L',
            role=JointRole.KNEE,
            parent_id='j13',
            pair_id='j17',
            x=center_x - 10,
            y=50,
            nx=-0.05,
            ny=0.25
        )
        self.add_joint(knee_l)
        
        knee_r = Joint(
            id='j17',
            name='Knee_R',
            role=JointRole.KNEE,
            parent_id='j16',
            pair_id='j14',
            x=center_x + 10,
            y=50,
            nx=0.05,
            ny=0.25
        )
        self.add_joint(knee_r)
        
        # Ankles
        ankle_l = Joint(
            id='j15',
            name='Ankle_L',
            role=JointRole.ANKLE,
            parent_id='j14',
            pair_id='j18',
            x=center_x - 10,
            y=10,
            nx=-0.05,
            ny=0.05
        )
        self.add_joint(ankle_l)
        
        ankle_r = Joint(
            id='j18',
            name='Ankle_R',
            role=JointRole.ANKLE,
            parent_id='j17',
            pair_id='j15',
            x=center_x + 10,
            y=10,
            nx=0.05,
            ny=0.05
        )
        self.add_joint(ankle_r)
        
        # Toes
        toe_l = Joint(
            id='j19',
            name='Toe_L',
            role=JointRole.TOE,
            parent_id='j15',
            pair_id='j20',
            x=center_x - 10,
            y=5,
            nx=-0.05,
            ny=0
        )
        self.add_joint(toe_l)
        
        toe_r = Joint(
            id='j20',
            name='Toe_R',
            role=JointRole.TOE,
            parent_id='j18',
            pair_id='j19',
            x=center_x + 10,
            y=5,
            nx=0.05,
            ny=0
        )
        self.add_joint(toe_r)
        
        # Generate bones
        self.generate_bones()
        
        # Update parameters
        self.parameters['floor_by_joint'] = 'Toe_L'
        self.parameters['top_by_joint'] = 'HeadTop'
    
    def create_preset_a_pose(self) -> None:
        """Create an A-pose preset skeleton"""
        self.create_preset_t_pose()
        
        # Adjust arm positions for A-pose
        for joint in self.joints.values():
            if joint.name == 'Shoulder_L':
                joint.x = -30
                joint.y = 140
            elif joint.name == 'Shoulder_R':
                joint.x = 30
                joint.y = 140
            elif joint.name == 'Elbow_L':
                joint.x = -40
                joint.y = 120
            elif joint.name == 'Elbow_R':
                joint.x = 40
                joint.y = 120
            elif joint.name == 'Wrist_L':
                joint.x = -35
                joint.y = 100
            elif joint.name == 'Wrist_R':
                joint.x = 35
                joint.y = 100
        
        self.generate_bones()
    
    def clear(self) -> None:
        """Clear all joints, bones, and contours"""
        self.joints.clear()
        self.bones.clear()
        self.contours.clear()
        self._next_id = 1
    
    def save_history(self) -> None:
        """Save current state to history"""
        state = self.to_dict()
        # Clear bones from history to save space (they can be regenerated)
        state['bones'] = []
        self._history = self._history[:self._history_index + 1]
        self._history.append(state)
        self._history_index = len(self._history) - 1
    
    def undo(self) -> bool:
        """Undo last action"""
        if self._history_index > 0:
            self._history_index -= 1
            self.from_dict(self._history[self._history_index])
            return True
        return False
    
    def redo(self) -> bool:
        """Redo last undone action"""
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self.from_dict(self._history[self._history_index])
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert skeleton to dictionary for JSON serialization"""
        return {
            'format': 'GMS-SkeletonStep1',
            'schemaVersion': 2,
            'version': '2.0.0',
            'parameters': self.parameters.copy(),
            'editor': {
                'joints': [j.to_dict() for j in self.joints.values()],
                'contours': [c.to_dict() for c in self.contours],
                'nextId': self._next_id
            },
            'skeleton3D': {
                'units': 'meters',
                'joints': [self._joint_to_3d(j) for j in self.joints.values()],
                'bones': [b.to_dict() for b in self.bones]
            },
            'stats': {
                'joints': len(self.joints),
                'bones': len(self.bones),
                'contours': len(self.contours)
            }
        }
    
    def _joint_to_3d(self, joint: Joint) -> Dict[str, Any]:
        """Convert 2D joint to 3D representation"""
        # For now, use 2D positions with Z=0
        # In a full implementation, this would use proper 3D coordinates
        return {
            'id': joint.id,
            'name': joint.name,
            'role': joint.role.value,
            'parent': joint.parent_id,
            'localPosition': {
                'x': 0,
                'y': 0,
                'z': 0
            },
            'worldPosition': {
                'x': 0,
                'y': 0,
                'z': 0
            }
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load skeleton from dictionary"""
        self.clear()
        
        # Load parameters
        if 'parameters' in data:
            self.parameters.update(data['parameters'])
        
        # Load joints
        if 'editor' in data and 'joints' in data['editor']:
            for joint_data in data['editor']['joints']:
                joint = Joint.from_dict(joint_data)
                self.joints[joint.id] = joint
                self._next_id = max(self._next_id, int(joint.id.replace('j', '')) + 1) if joint.id.startswith('j') else self._next_id + 1
        
        # Load contours
        if 'editor' in data and 'contours' in data['editor']:
            for contour_data in data['editor']['contours']:
                contour = BodyContour.from_dict(contour_data)
                self.contours.append(contour)
        
        # Load bones
        if 'skeleton3D' in data and 'bones' in data['skeleton3D']:
            for bone_data in data['skeleton3D']['bones']:
                bone = Bone.from_dict(bone_data)
                self.bones.append(bone)
        
        if 'editor' in data and 'nextId' in data['editor']:
            self._next_id = data['editor']['nextId']
        
        # Calculate 3D world positions from 2D coordinates
        self.calculate_world_positions(scale=1.0)
    
    def to_json(self, indent: int = 2) -> str:
        """Export skeleton to JSON string"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Skeleton':
        """Create skeleton from JSON string"""
        data = json.loads(json_str)
        skeleton = cls()
        skeleton.from_dict(data)
        return skeleton
    
    def save_to_file(self, path: str) -> bool:
        """Save skeleton to file"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.to_json())
            return True
        except Exception as e:
            print(f"Error saving skeleton: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, path: str) -> Optional['Skeleton']:
        """Load skeleton from file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            skeleton = cls()
            skeleton.from_dict(data)
            return skeleton
        except Exception as e:
            print(f"Error loading skeleton: {e}")
            return None
    
    def get_joint_count(self) -> int:
        """Get number of joints"""
        return len(self.joints)
    
    def get_bone_count(self) -> int:
        """Get number of bones"""
        return len(self.bones)


def create_skeleton_from_json_file(path: str) -> Optional[Skeleton]:
    """Convenience function to create skeleton from JSON file"""
    return Skeleton.load_from_file(path)
