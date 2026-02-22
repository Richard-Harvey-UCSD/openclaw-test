using UnityEditor;
using UnityEngine;

namespace GestureEngine.Editor
{
    [CustomPropertyDrawer(typeof(Binding))]
    public class GestureBindingDrawer : PropertyDrawer
    {
        private static readonly string[] DefaultGestures =
        {
            "open_hand", "fist", "thumbs_up", "peace", "pointing", "rock_on", "ok_sign",
            // Sequences
            "release", "grab", "wave", "peace_out", "pinch_release", "point_and_click",
            // Trajectories
            "swipe_left", "swipe_right", "swipe_up", "swipe_down",
            "circle_cw", "circle_ccw", "z_pattern",
            // Bimanual
            "pinch_zoom", "clap", "frame", "conduct_up", "conduct_down"
        };

        public override float GetPropertyHeight(SerializedProperty property, GUIContent label)
        {
            if (!property.isExpanded)
                return EditorGUIUtility.singleLineHeight;

            int lines = 7; // base fields
            var onTriggered = property.FindPropertyRelative("onTriggered");
            var onTriggeredConf = property.FindPropertyRelative("onTriggeredWithConfidence");
            float eventHeight = EditorGUI.GetPropertyHeight(onTriggered)
                              + EditorGUI.GetPropertyHeight(onTriggeredConf);
            return lines * (EditorGUIUtility.singleLineHeight + 2) + eventHeight + 10;
        }

        public override void OnGUI(Rect position, SerializedProperty property, GUIContent label)
        {
            EditorGUI.BeginProperty(position, label, property);

            var enabledProp = property.FindPropertyRelative("enabled");
            var typeProp = property.FindPropertyRelative("eventType");
            var nameProp = property.FindPropertyRelative("gestureName");
            var confProp = property.FindPropertyRelative("minimumConfidence");
            var coolProp = property.FindPropertyRelative("cooldown");

            float lineH = EditorGUIUtility.singleLineHeight + 2;
            var rect = new Rect(position.x, position.y, position.width, EditorGUIUtility.singleLineHeight);

            // Foldout with enabled toggle
            string headerLabel = $"{nameProp.stringValue} ({typeProp.enumDisplayNames[typeProp.enumValueIndex]})";
            if (!enabledProp.boolValue) headerLabel += " [Disabled]";

            property.isExpanded = EditorGUI.Foldout(rect, property.isExpanded, headerLabel, true);

            if (!property.isExpanded)
            {
                EditorGUI.EndProperty();
                return;
            }

            EditorGUI.indentLevel++;
            rect.y += lineH;

            EditorGUI.PropertyField(rect, enabledProp);
            rect.y += lineH;

            EditorGUI.PropertyField(rect, typeProp);
            rect.y += lineH;

            // Gesture name with dropdown
            var nameRect = rect;
            var dropRect = new Rect(nameRect.xMax - 20, nameRect.y, 20, nameRect.height);
            nameRect.width -= 22;
            EditorGUI.PropertyField(nameRect, nameProp);

            if (GUI.Button(dropRect, "▼", EditorStyles.miniButton))
            {
                var menu = new GenericMenu();
                foreach (var g in DefaultGestures)
                {
                    string gesture = g;
                    menu.AddItem(new GUIContent(gesture), nameProp.stringValue == gesture,
                        () => { nameProp.stringValue = gesture; property.serializedObject.ApplyModifiedProperties(); });
                }
                menu.ShowAsContext();
            }
            rect.y += lineH;

            EditorGUI.PropertyField(rect, confProp);
            rect.y += lineH;

            EditorGUI.PropertyField(rect, coolProp);
            rect.y += lineH;

            var onTriggered = property.FindPropertyRelative("onTriggered");
            var onTriggeredConf = property.FindPropertyRelative("onTriggeredWithConfidence");

            EditorGUI.PropertyField(rect, onTriggered);
            rect.y += EditorGUI.GetPropertyHeight(onTriggered) + 2;

            EditorGUI.PropertyField(rect, onTriggeredConf);

            EditorGUI.indentLevel--;
            EditorGUI.EndProperty();
        }
    }
}
