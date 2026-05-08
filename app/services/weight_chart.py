from aiogram.types import BufferedInputFile
import io
from app.config import TIMEZONE
import pytz
from app.config import FAMILY_USER_ID
from app.services.stats import get_weights
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend


async def create_weight_chart(session: AsyncSession, user_id: int) -> BufferedInputFile:
    """Create a weight chart image showing all weight records over time"""
    # Get all weight records
    all_weights = await get_weights(session, user_id, limit=1000)

    if not all_weights or len(all_weights) < 2:
        return None

    # Prepare data (reverse to get chronological order)
    weights = list(reversed(all_weights))
    dates = [w.created_at for w in weights]
    weight_values = [w.weight_g for w in weights]

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot the data
    ax.plot(dates, weight_values, 'b-o', linewidth=2,
            markersize=6, color='#2196F3')

    # Fill area under the line
    ax.fill_between(dates, weight_values, alpha=0.1, color='#2196F3')

    # Format dates on x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())

    # Rotate date labels for better readability
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Add labels and title
    ax.set_xlabel('Дата', fontsize=12)
    ax.set_ylabel('Вес (г)', fontsize=12)
    ax.set_title('📊 График изменения веса ребенка',
                 fontsize=14, fontweight='bold')

    # Add grid for better readability
    ax.grid(True, alpha=0.3, linestyle='--')

    # Add weight values on each point
    for i, (date, weight) in enumerate(zip(dates, weight_values)):
        ax.annotate(
            f'{weight:.0f}',
            xy=(date, weight),
            xytext=(0, 10),
            textcoords='offset points',
            ha='center',
            fontsize=8,
            fontweight='bold'
        )

    # Adjust layout
    plt.tight_layout()

    # Save to bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)

    # Create input file for Telegram
    chart_file = BufferedInputFile(
        file=buf.read(),
        filename='weight_chart.png'
    )

    return chart_file
