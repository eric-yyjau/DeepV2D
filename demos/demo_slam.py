import sys
sys.path.append('deepv2d')
# sys.path.append('')

import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt

import cv2
import os
import time
import argparse
import glob

from pathlib import Path

from data_stream.scannet import ScanNet
from data_stream.nyuv2 import NYUv2
from data_stream.tum_rgbd import TUM_RGBD
from data_stream.kitti import KittiRaw

from core import config
from slam import DeepV2DSLAM
from slam_kitti import DeepV2DSLAM_KITTI
from tqdm import tqdm


# from KITTI_odometry_evaluation_tool.tools.pose_evaluation_utils import rot2quat
def matrix_to_quatVec(mat):
    # print(f"mat: {mat}")
    rotation = mat[:3,:3]
    trans = mat[:3,3]
    # from pyquaternion import Quaternion
    # qua = Quaternion(matrix=rotation)
    # vect = np.concatenate((trans, qua.elements), axis=0)
    qua = rot2quat(rotation)
    vect = np.concatenate((trans, qua), axis=0)
    return vect


def main(args):

    if args.dataset == 'kitti':
        cfg = config.cfg_from_file('cfgs/kitti.yaml')
 
        model = 'models/kitti.ckpt'
        slam = DeepV2DSLAM_KITTI(cfg, model, n_keyframes=args.n_keyframes)

        # dataset_dir = '/media/datadrive/data/KITTI/raw'
        dataset_dir = '/media/datadrive/data/KITTI/raw'
        db = KittiRaw(dataset_dir)

        if args.sequence is None:
            args.sequence = '2011_09_26_drive_0002'

        
    else:
        cfg = config.cfg_from_file('cfgs/nyu.yaml')
        model = 'models/nyu_scannet.ckpt'
        slam = DeepV2DSLAM(cfg, model, n_keyframes=args.n_keyframes, rate=args.rate, use_fcrn=True)

        if args.dataset == 'scannet':
            dataset_dir = 'data/slam/scannet/'
            db = ScanNet(dataset_dir)

        elif args.dataset == 'nyu':
            dataset_dir = 'data/slam/nyu/'
            db = NYUv2(dataset_dir)

        elif args.dataset == 'tum':
            dataset_dir = 'data/slam/tum'
            db = TUM_RGBD(dataset_dir)

        else:
            print("Dataset must be [kitti, scannet, nyu, or tum]")

        if args.sequence is None:
            args.sequence = os.listdir(dataset_dir)[0]


    with tf.Session() as sess:

        # initialize the tracker and restore weights
        slam.set_session(sess)
        slam.start_visualization(args.cinematic, args.render_path, args.clear_points)
        # print(f"len of dataset: {len(db)}")

        for i, (image, intrinsics, tstamp) in tqdm( enumerate (db.iterate_sequence(args.sequence) ) ):
            slam(image, intrinsics, float(tstamp))
            # if i > 10:
            #     break
        poses = slam.poses
        tstamps = np.array(slam.tstamps).reshape(-1, 1)
        poses = np.array(poses).reshape(-1, 16)
        poses = poses[:,:12]
        print(f"poses: {poses}")
        print(f"poses: {poses.shape}")
        print(f"tstamps: {tstamps.shape}")
        t_poses = np.concatenate((tstamps, poses), axis=1)
        Path(args.save_poses).mkdir(exist_ok=True, parents=True)
        np.savetxt(f"{args.save_poses}/poses.txt", t_poses, delimiter=" ")



if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', default='nyu', help='which dataset to use')
    parser.add_argument('--sequence', help='what video in the dataset to use')
    
    # slam arguments
    parser.add_argument('--n_keyframes', type=int, default=3, help='number of keyframes to use')
    parser.add_argument('--rate', type=int, default=2, help='rate at which to add new frames')

    # visualization arguments
    parser.add_argument('--cinematic', action='store_true', help='run visualization in cinematic mode')
    parser.add_argument('--render_path', help='where to save rendered images, if None do not save')
    parser.add_argument('--save_poses', default="./", help='where to save predicted poses, if None do not save')
    parser.add_argument('--clear_points', action='store_true', help='only display the point cloud for the latest keyframe')

    args = parser.parse_args()
    main(args)