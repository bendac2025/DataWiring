import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# --- Page Configuration ---
st.set_page_config(page_title="Bendac LED Planner", page_icon="🔌", layout="wide")

# --- Constants ---
PIXEL_CAPACITY_PER_PORT = 650000  # As requested

# --- Helper Functions ---
def generate_topology(panels_w, panels_h, panel_res_w, panel_res_h, max_pixels):
    """
    Generates a vertical snake topology (Up col 0, Down col 1, Up col 2...).
    Returns a list of dicts with panel coordinates and port assignments.
    """
    panel_pixels = panel_res_w * panel_res_h
    
    topology_data = []
    
    current_port = 1
    current_port_pixels = 0
    
    # Iterate columns (x)
    for x in range(panels_w):
        # Determine direction: Even columns GO UP (0 to H-1), Odd columns GO DOWN (H-1 to 0)
        # Assuming standard cabling start at Bottom-Left
        if x % 2 == 0:
            y_range = range(panels_h) # 0, 1, 2...
        else:
            y_range = range(panels_h - 1, -1, -1) # 5, 4, 3...
            
        for y in y_range:
            # Check capacity
            if current_port_pixels + panel_pixels > max_pixels:
                current_port += 1
                current_port_pixels = 0
            
            # Assign panel
            topology_data.append({
                "x": x,
                "y": y,
                "port": current_port,
                "panel_id": f"{x+1}-{y+1}"
            })
            
            current_port_pixels += panel_pixels
            
    return pd.DataFrame(topology_data)

def plot_wiring_diagram(topology_df, panels_w, panels_h):
    """
    Plots the grid of panels colored by Port ID.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Create a grid
    ax.set_xlim(-0.5, panels_w - 0.5)
    ax.set_ylim(-0.5, panels_h - 0.5)
    
    # Unique ports for coloring
    ports = topology_df['port'].unique()
    colors = plt.cm.get_cmap('tab20', len(ports))
    
    for _, row in topology_df.iterrows():
        x, y = row['x'], row['y']
        port = row['port']
        
        # Draw Panel Rectangle
        # Note: color maps allow retrieving a color by index/value
        # We normalize port number to pick a color
        color_idx = (port - 1) % 20
        rect = patches.Rectangle((x - 0.45, y - 0.45), 0.9, 0.9, 
                                 linewidth=1, edgecolor='white', 
                                 facecolor=colors(color_idx))
        ax.add_patch(rect)
        
        # Add Port Label Text
        ax.text(x, y, f"P{port}", ha='center', va='center', 
                color='white', fontweight='bold', fontsize=8)

    ax.set_aspect('equal')
    ax.set_title("Data Cabling Topology (Port Map)", fontsize=14)
    ax.set_xlabel("Columns (Width)")
    ax.set_ylabel("Rows (Height)")
    ax.set_xticks(range(panels_w))
    ax.set_yticks(range(panels_h))
    ax.grid(False)
    
    # Remove axis spines for cleaner look
    for spine in ax.spines.values():
        spine.set_visible(False)
        
    return fig

# --- Main App Interface ---
st.title("🔌 Bendac LED Data Cabling Planner")

# --- Sidebar ---
st.sidebar.header("1. Configuration")
uploaded_file = st.sidebar.file_uploader("Load Database (CSV)", type="csv")
processor_type = st.sidebar.selectbox("Processor", ["Novastar MCTRL4K", "Novastar VX1000", "Novastar H-Series"])

st.sidebar.markdown("---")
st.sidebar.header("2. Screen Size")
col1, col2 = st.sidebar.columns(2)
with col1:
    panels_w = st.number_input("Width (Panels)", min_value=1, value=8, step=1)
with col2:
    panels_h = st.number_input("Height (Panels)", min_value=1, value=4, step=1)

# --- Logic ---
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # 1. Product Selection
    # Create a unique label combining Name and Pitch (e.g., "Bendac Krystl Max - 2.6mm")
    df['Display Name'] = df['Product Name'] + " - " + df['Pitch(mm)'].astype(str) + "mm"
    
    selected_name = st.selectbox("Select Panel Model:", df['Display Name'].unique())
    
    # Get specs for selected panel
    specs = df[df['Display Name'] == selected_name].iloc[0]
    
    # Extract Data
    res_w = int(specs['ResW(px)'])
    res_h = int(specs['ResH(px)'])
    power_w = float(specs['Power(W)'])
    
    # 2. Calculations
    total_panels = panels_w * panels_h
    total_res_w = panels_w * res_w
    total_res_h = panels_h * res_h
    total_pixels = total_panels * (res_w * res_h)
    total_power_kw = (total_panels * power_w) / 1000
    
    # Display Specs
    st.markdown("### 📊 Screen Specifications")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Screen Resolution", f"{total_res_w} x {total_res_h} px")
    m2.metric("Total Panels", total_panels)
    m3.metric("Total Pixels", f"{total_pixels:,}")
    m4.metric("Max Power Consumption", f"{total_power_kw:.2f} kW")
    
    st.divider()
    
    # 3. Data Topology Engine
    st.subheader("🔗 Data Topology & Port Calculation")
    
    # Run the snake algorithm
    topology_df = generate_topology(panels_w, panels_h, res_w, res_h, PIXEL_CAPACITY_PER_PORT)
    
    # Calculate required ports
    num_ports = topology_df['port'].max()
    
    # Show Results
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.info(f"**Required Ports:** {num_ports}")
        st.write(f"**Capacity per Port:** {PIXEL_CAPACITY_PER_PORT:,} px")
        
        # Detailed Usage Table
        port_counts = topology_df.groupby('port').size().reset_index(name='Panels Count')
        port_counts['Pixel Load'] = port_counts['Panels Count'] * (res_w * res_h)
        port_counts['Utilization (%)'] = (port_counts['Pixel Load'] / PIXEL_CAPACITY_PER_PORT * 100).round(1)
        st.write("Port Usage:")
        st.dataframe(port_counts, hide_index=True)

    with c2:
        # Visualize
        st.write("**Wiring Diagram (Port Map)**")
        fig = plot_wiring_diagram(topology_df, panels_w, panels_h)
        st.pyplot(fig)
        st.caption("Visual representation of cabling path (Vertical Snake: Up -> Right -> Down)")

else:
    st.info("Awaiting CSV file upload...")
