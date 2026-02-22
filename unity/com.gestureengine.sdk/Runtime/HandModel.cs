using System;
using UnityEngine;

namespace GestureEngine
{
    /// <summary>
    /// 21-landmark hand model matching MediaPipe hand landmark indices.
    /// </summary>
    public class HandModel
    {
        public const int LandmarkCount = 21;

        // Landmark indices
        public const int Wrist = 0;
        public const int ThumbCMC = 1;
        public const int ThumbMCP = 2;
        public const int ThumbIP = 3;
        public const int ThumbTip = 4;
        public const int IndexMCP = 5;
        public const int IndexPIP = 6;
        public const int IndexDIP = 7;
        public const int IndexTip = 8;
        public const int MiddleMCP = 9;
        public const int MiddlePIP = 10;
        public const int MiddleDIP = 11;
        public const int MiddleTip = 12;
        public const int RingMCP = 13;
        public const int RingPIP = 14;
        public const int RingDIP = 15;
        public const int RingTip = 16;
        public const int PinkyMCP = 17;
        public const int PinkyPIP = 18;
        public const int PinkyDIP = 19;
        public const int PinkyTip = 20;

        /// <summary>Finger tip landmark indices.</summary>
        public static readonly int[] FingerTips = { ThumbTip, IndexTip, MiddleTip, RingTip, PinkyTip };

        /// <summary>Finger PIP/IP landmark indices (for extension detection).</summary>
        public static readonly int[] FingerPIPs = { ThumbIP, IndexPIP, MiddlePIP, RingPIP, PinkyPIP };

        /// <summary>
        /// Bone connections for rendering lines between landmarks.
        /// Each pair is (startIndex, endIndex).
        /// </summary>
        public static readonly int[,] BoneConnections = {
            // Thumb
            { Wrist, ThumbCMC }, { ThumbCMC, ThumbMCP }, { ThumbMCP, ThumbIP }, { ThumbIP, ThumbTip },
            // Index
            { Wrist, IndexMCP }, { IndexMCP, IndexPIP }, { IndexPIP, IndexDIP }, { IndexDIP, IndexTip },
            // Middle
            { Wrist, MiddleMCP }, { MiddleMCP, MiddlePIP }, { MiddlePIP, MiddleDIP }, { MiddleDIP, MiddleTip },
            // Ring
            { Wrist, RingMCP }, { RingMCP, RingPIP }, { RingPIP, RingDIP }, { RingDIP, RingTip },
            // Pinky
            { Wrist, PinkyMCP }, { PinkyMCP, PinkyPIP }, { PinkyPIP, PinkyDIP }, { PinkyDIP, PinkyTip },
            // Palm
            { IndexMCP, MiddleMCP }, { MiddleMCP, RingMCP }, { RingMCP, PinkyMCP },
        };

        /// <summary>The 21 3D landmark positions.</summary>
        public Vector3[] Landmarks { get; private set; }

        /// <summary>Hand index (0 = first hand, 1 = second).</summary>
        public int HandIndex { get; set; }

        /// <summary>Timestamp of last update.</summary>
        public double LastUpdateTime { get; private set; }

        public HandModel()
        {
            Landmarks = new Vector3[LandmarkCount];
        }

        /// <summary>
        /// Update landmarks from a flat float array (63 values).
        /// </summary>
        public void UpdateFromFlatArray(float[] data, double timestamp)
        {
            if (data == null || data.Length < LandmarkCount * 3)
                return;

            for (int i = 0; i < LandmarkCount; i++)
            {
                Landmarks[i] = new Vector3(
                    data[i * 3],
                    data[i * 3 + 1],
                    data[i * 3 + 2]
                );
            }
            LastUpdateTime = timestamp;
        }

        /// <summary>
        /// Check if a finger is extended (tip farther from wrist than PIP).
        /// </summary>
        public bool IsFingerExtended(int fingerIndex)
        {
            if (fingerIndex < 0 || fingerIndex > 4) return false;
            int tipIdx = FingerTips[fingerIndex];
            int pipIdx = FingerPIPs[fingerIndex];
            float tipDist = Vector3.Distance(Landmarks[tipIdx], Landmarks[Wrist]);
            float pipDist = Vector3.Distance(Landmarks[pipIdx], Landmarks[Wrist]);
            return tipDist > pipDist;
        }

        /// <summary>Get the centroid of all landmarks.</summary>
        public Vector3 Centroid
        {
            get
            {
                Vector3 sum = Vector3.zero;
                for (int i = 0; i < LandmarkCount; i++)
                    sum += Landmarks[i];
                return sum / LandmarkCount;
            }
        }
    }
}
