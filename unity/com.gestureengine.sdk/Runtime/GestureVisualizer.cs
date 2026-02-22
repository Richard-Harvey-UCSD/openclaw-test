using System.Collections.Generic;
using UnityEngine;

namespace GestureEngine
{
    /// <summary>
    /// Debug visualization of hand landmarks as spheres and bones as lines.
    /// Works in both Scene and Game view.
    /// </summary>
    public class GestureVisualizer : MonoBehaviour
    {
        [Header("Appearance")]
        [SerializeField] private float landmarkSize = 0.008f;
        [SerializeField] private float boneWidth = 0.003f;
        [SerializeField] private Color landmarkColor = Color.cyan;
        [SerializeField] private Color boneColor = new Color(0.2f, 0.8f, 0.2f, 0.8f);
        [SerializeField] private Color thumbColor = new Color(1f, 0.5f, 0f, 1f);
        [SerializeField] private Color fingertipColor = Color.red;

        [Header("Transform")]
        [SerializeField] private Vector3 offset = Vector3.zero;
        [SerializeField] private float scale = 1f;

        private Dictionary<int, HandRenderData> _handRenders = new Dictionary<int, HandRenderData>();
        private Material _lineMaterial;

        private class HandRenderData
        {
            public HandModel Model;
            public GameObject[] Spheres;
            public LineRenderer[] Bones;
            public float LastUpdate;
        }

        /// <summary>
        /// Update the visualization for a given hand model.
        /// Called by GestureManager when hand_update events arrive.
        /// </summary>
        public void UpdateHand(HandModel hand)
        {
            if (!_handRenders.TryGetValue(hand.HandIndex, out var data))
            {
                data = CreateHandRender(hand.HandIndex);
                _handRenders[hand.HandIndex] = data;
            }

            data.Model = hand;
            data.LastUpdate = Time.time;

            // Update sphere positions
            for (int i = 0; i < HandModel.LandmarkCount; i++)
            {
                Vector3 pos = hand.Landmarks[i] * scale + offset;
                data.Spheres[i].transform.position = pos;

                // Color coding
                var renderer = data.Spheres[i].GetComponent<MeshRenderer>();
                if (System.Array.IndexOf(HandModel.FingerTips, i) >= 0)
                    renderer.material.color = fingertipColor;
                else if (i >= HandModel.ThumbCMC && i <= HandModel.ThumbTip)
                    renderer.material.color = thumbColor;
                else
                    renderer.material.color = landmarkColor;
            }

            // Update bone lines
            int boneCount = HandModel.BoneConnections.GetLength(0);
            for (int b = 0; b < boneCount; b++)
            {
                int start = HandModel.BoneConnections[b, 0];
                int end = HandModel.BoneConnections[b, 1];
                var lr = data.Bones[b];
                lr.SetPosition(0, hand.Landmarks[start] * scale + offset);
                lr.SetPosition(1, hand.Landmarks[end] * scale + offset);
            }
        }

        private HandRenderData CreateHandRender(int handIndex)
        {
            var root = new GameObject($"Hand_{handIndex}_Viz");
            root.transform.SetParent(transform);

            var data = new HandRenderData
            {
                Spheres = new GameObject[HandModel.LandmarkCount],
                Bones = new LineRenderer[HandModel.BoneConnections.GetLength(0)]
            };

            // Create landmark spheres
            for (int i = 0; i < HandModel.LandmarkCount; i++)
            {
                var sphere = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                sphere.name = $"Landmark_{i}";
                sphere.transform.SetParent(root.transform);
                sphere.transform.localScale = Vector3.one * landmarkSize;

                // Remove collider for performance
                var col = sphere.GetComponent<Collider>();
                if (col != null) Destroy(col);

                data.Spheres[i] = sphere;
            }

            // Create bone line renderers
            int boneCount = HandModel.BoneConnections.GetLength(0);
            for (int b = 0; b < boneCount; b++)
            {
                var boneObj = new GameObject($"Bone_{b}");
                boneObj.transform.SetParent(root.transform);

                var lr = boneObj.AddComponent<LineRenderer>();
                lr.positionCount = 2;
                lr.startWidth = boneWidth;
                lr.endWidth = boneWidth;
                lr.material = GetLineMaterial();
                lr.startColor = boneColor;
                lr.endColor = boneColor;
                lr.useWorldSpace = true;

                data.Bones[b] = lr;
            }

            return data;
        }

        private Material GetLineMaterial()
        {
            if (_lineMaterial == null)
            {
                _lineMaterial = new Material(Shader.Find("Sprites/Default"));
            }
            return _lineMaterial;
        }

        private void LateUpdate()
        {
            // Hide hands that haven't been updated recently
            foreach (var kvp in _handRenders)
            {
                bool visible = (Time.time - kvp.Value.LastUpdate) < 0.5f;
                foreach (var sphere in kvp.Value.Spheres)
                {
                    if (sphere != null)
                        sphere.SetActive(visible);
                }
                foreach (var bone in kvp.Value.Bones)
                {
                    if (bone != null)
                        bone.enabled = visible;
                }
            }
        }

        private void OnDrawGizmos()
        {
            // Also draw in Scene view via Gizmos
            foreach (var kvp in _handRenders)
            {
                var data = kvp.Value;
                if (data.Model == null) continue;
                if (Time.time - data.LastUpdate > 0.5f) continue;

                Gizmos.color = landmarkColor;
                for (int i = 0; i < HandModel.LandmarkCount; i++)
                {
                    Vector3 pos = data.Model.Landmarks[i] * scale + offset;
                    Gizmos.DrawSphere(pos, landmarkSize * 0.5f);
                }

                Gizmos.color = boneColor;
                int boneCount = HandModel.BoneConnections.GetLength(0);
                for (int b = 0; b < boneCount; b++)
                {
                    int s = HandModel.BoneConnections[b, 0];
                    int e = HandModel.BoneConnections[b, 1];
                    Gizmos.DrawLine(
                        data.Model.Landmarks[s] * scale + offset,
                        data.Model.Landmarks[e] * scale + offset
                    );
                }
            }
        }

        private void OnDestroy()
        {
            foreach (var kvp in _handRenders)
            {
                foreach (var sphere in kvp.Value.Spheres)
                {
                    if (sphere != null) Destroy(sphere);
                }
                foreach (var bone in kvp.Value.Bones)
                {
                    if (bone != null) Destroy(bone.gameObject);
                }
            }
            if (_lineMaterial != null)
                Destroy(_lineMaterial);
        }
    }
}
