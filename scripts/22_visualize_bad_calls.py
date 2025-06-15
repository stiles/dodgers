import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
import os

BALL_RADIUS_FEET = 1.45 / 12

def visualize_called_strikes(file_path, output_dir):
    """
    Visualizes all called strikes, highlighting correct vs. incorrect calls.

    Args:
        file_path (str): The path to the JSON file with pitch data.
        output_dir (str): The directory to save the plot image.
    """
    try:
        df = pd.read_json(file_path)
    except Exception as e:
        print(f"Error reading or parsing {file_path}: {e}")
        return

    if df.empty:
        print("No pitch data available.")
        return

    # Filter for all called strikes
    df_called_strikes = df[df['pitch_call'] == 'called_strike'].copy()

    if df_called_strikes.empty:
        print("No called strikes found to visualize.")
        return

    # --- Strike Zone Dimensions ---
    # The catcher's view is from behind the plate.
    # The x-axis (px) is horizontal, y-axis (pz) is vertical.
    # Horizontal boundaries are constant (in feet).
    sz_width = 0.708 * 2  # -0.708 to +0.708 feet
    # Vertical boundaries (sz_top, sz_bot) vary by batter and pitch.
    # We'll use the average for visualization.
    avg_sz_top = df['sz_top'].mean()
    avg_sz_bot = df['sz_bot'].mean()
    sz_height = avg_sz_top - avg_sz_bot

    # Re-classify pitches based on the AVERAGE strike zone for visual consistency.
    # The original 'pitch_in_zone' is more accurate for stats, but for this plot,
    # we use a recalculated version to match the single rectangle being drawn.
    sz_left = -sz_width / 2
    sz_right = sz_width / 2

    def is_in_visual_zone(row):
        px, pz = row['px'], row['pz']
        if pd.isna(px) or pd.isna(pz):
            return False
        
        # Find closest point on the average strike zone rectangle
        closest_x = max(sz_left, min(sz_right, px))
        closest_z = max(avg_sz_bot, min(avg_sz_top, pz))
        
        # Check if distance from pitch center to closest point is within ball radius
        dist_sq = (px - closest_x)**2 + (pz - closest_z)**2
        return dist_sq <= (BALL_RADIUS_FEET**2)

    df_called_strikes['visual_in_zone'] = df_called_strikes.apply(is_in_visual_zone, axis=1)

    df_called_strikes['call_type'] = df_called_strikes['visual_in_zone'].apply(
        lambda x: 'In Zone (Correct)' if x else 'Out of Zone (Incorrect)'
    )

    # --- Plotting ---
    sns.set_style("whitegrid")
    fig, ax = plt.subplots(figsize=(8, 10))

    # Plot all called strikes, colored by whether the call was correct
    sns.scatterplot(
        data=df_called_strikes,
        x='px',
        y='pz',
        hue='call_type',
        palette={'In Zone (Correct)': 'green', 'Out of Zone (Incorrect)': 'red'},
        s=50,
        alpha=0.6,
        ax=ax
    )

    # Draw the average strike zone rectangle
    strike_zone = patches.Rectangle(
        (-sz_width / 2, avg_sz_bot),
        sz_width,
        sz_height,
        linewidth=2,
        edgecolor='black',
        facecolor='none',
        linestyle='--',
        label='Average Strike Zone'
    )
    ax.add_patch(strike_zone)

    # --- Formatting ---
    ax.set_title('Called Strikes (Catcher\'s View)', fontsize=16, fontweight='bold')
    ax.set_xlabel('Horizontal Position (feet from center of plate)', fontsize=12)
    ax.set_ylabel('Vertical Position (feet from ground)', fontsize=12)
    ax.set_aspect('equal', adjustable='box')

    # Set plot limits to give some padding around the zone
    plt.xlim(-2.5, 2.5)
    plt.ylim(0, 5)

    # Place legend outside the plot
    ax.legend(title='Call Type', bbox_to_anchor=(1.05, 1), loc='upper left')

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'called_strikes_visualization.png')

    plt.tight_layout(rect=[0, 0, 0.85, 1]) # Adjust layout to make room for legend
    plt.savefig(output_path, dpi=300)
    plt.close()

    print(f"Plot saved to {output_path}")

if __name__ == "__main__":
    file_path = 'data/pitches/dodgers_pitches_2025.json'
    output_dir = 'images'
    visualize_called_strikes(file_path, output_dir) 