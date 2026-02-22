using UnityEditor;
using UnityEngine;

namespace GestureEngine.Editor
{
    [CustomEditor(typeof(GestureManager))]
    public class GestureManagerEditor : UnityEditor.Editor
    {
        private bool _showEvents = true;
        private bool _showDebug;

        public override void OnInspectorGUI()
        {
            var manager = (GestureManager)target;

            // Status bar
            EditorGUILayout.BeginHorizontal(EditorStyles.helpBox);
            var statusColor = manager.IsConnected ? Color.green : Color.red;
            var prevColor = GUI.color;
            GUI.color = statusColor;
            GUILayout.Label(manager.IsConnected ? "● Connected" : "● Disconnected",
                EditorStyles.boldLabel, GUILayout.Width(120));
            GUI.color = prevColor;

            if (Application.isPlaying)
            {
                if (!manager.IsConnected)
                {
                    if (GUILayout.Button("Connect", GUILayout.Width(80)))
                        manager.Connect();
                }
                else
                {
                    if (GUILayout.Button("Disconnect", GUILayout.Width(80)))
                        manager.Disconnect();
                }
            }
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.Space();

            // Available gestures
            if (manager.IsConnected && manager.AvailableGestures != null && manager.AvailableGestures.Length > 0)
            {
                EditorGUILayout.LabelField("Available Gestures", EditorStyles.boldLabel);
                EditorGUI.indentLevel++;
                foreach (var g in manager.AvailableGestures)
                    EditorGUILayout.LabelField(g);
                EditorGUI.indentLevel--;
                EditorGUILayout.Space();
            }

            // Draw default inspector
            DrawDefaultInspector();
        }
    }
}
