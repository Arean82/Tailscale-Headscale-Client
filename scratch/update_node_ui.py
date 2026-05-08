import xml.etree.ElementTree as ET

ui_path = r"c:\Users\user\Documents\GitHub\Tailscale-Headscale-Client\pygui\dialogs\node.ui"

# Parse XML
tree = ET.parse(ui_path)
root = tree.getroot()

# Find the gridLayout element
grid_layout = root.find(".//layout[@name='gridLayout']")

if grid_layout is not None:
    # Shift existing items
    for item in grid_layout.findall("item"):
        row = item.attrib.get("row")
        if row == "2":
            item.attrib["row"] = "3"
        elif row == "3":
            item.attrib["row"] = "4"
        elif row == "4":
            item.attrib["row"] = "5"
            
    # Create labelHostname item
    item_lbl = ET.Element("item", row="2", column="0")
    widget_lbl = ET.SubElement(item_lbl, "widget", {"class": "QLabel", "name": "labelHostname"})
    prop_font = ET.SubElement(widget_lbl, "property", name="font")
    font = ET.SubElement(prop_font, "font")
    ET.SubElement(font, "pointsize").text = "9"
    ET.SubElement(font, "bold").text = "true"
    prop_text = ET.SubElement(widget_lbl, "property", name="text")
    ET.SubElement(prop_text, "string").text = "Custom Hostname :"
    
    # Create lineEditHostname item
    item_edit = ET.Element("item", row="2", column="1")
    widget_edit = ET.SubElement(item_edit, "widget", {"class": "QLineEdit", "name": "lineEditHostname"})
    prop_placeholder = ET.SubElement(widget_edit, "property", name="placeholderText")
    ET.SubElement(prop_placeholder, "string").text = "e.g. my-node-override"
    
    # Append new items
    grid_layout.append(item_lbl)
    grid_layout.append(item_edit)
    
    # Write back
    tree.write(ui_path, encoding="utf-8", xml_declaration=True)
    print("SUCCESS")
else:
    print("gridLayout not found")
