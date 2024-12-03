import argparse
import gzip
import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader  # Import ImageReader
from io import BytesIO
"""
In reportlab, the x and y coordinates for c.drawString(x, y, text) are measured in points.

Points in ReportLab
1 point = 1/72 inch.
The origin (0, 0) is at the bottom-left corner of the page.
The x coordinate increases as you move right.
The y coordinate increases as you move up.
Example for Letter Page Size (8.5 x 11 inches)
For an 8.5 x 11 inch letter-sized page (612 x 792 points):

width = 612 points (8.5 inches * 72 points/inch)
height = 792 points (11 inches * 72 points/inch)
So if you want to place text at 1 inch from the left and 2 inches from the bottom, you’d use:
"""

def load_gzipped_jsonl_to_dataframe(file_path):
    """
    Loads a gzipped JSONL file into a Pandas DataFrame.

    Parameters:
    - file_path (str): The path to the gzipped JSONL file.

    Returns:
    - pd.DataFrame: A Pandas DataFrame containing the data from the JSONL file.
    """
    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
        # Read the gzipped JSONL file into a Pandas DataFrame
        df = pd.read_json(f, lines=True)

    return df

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="A program to analyzer GA4 event data")

    # Add arguments for name, age, and greet flag
    parser.add_argument('--file', type=str, required=True, help="data file")
    parser.add_argument('--top_bucket_size', type=int, required=True, help="bucket size to capture the top values")
    parser.add_argument('--report')

    # Parse the arguments
    args = parser.parse_args()
    filename = f'{args.file}'.replace("/", "").replace(".","")
    # File path for the pickle file
    pickle_file = f'{filename}.pkl'

    # Load the data
    # Check if the pickle file exists
    if os.path.exists(f'./data/{pickle_file}'):
        # Load the DataFrame from the pickle file
        df = pd.read_pickle(f'./data/{pickle_file}')
        print("Loaded DataFrame from pickle file.")
    else:
        # Create a new DataFrame if the pickle file doesn't exist
        df = load_gzipped_jsonl_to_dataframe(args.file)
        # Serialize the DataFrame to a pickle file
        df.to_pickle(f'./data/{pickle_file}')

    # Specify the PDF file
    pdf_filename = f'./output/GA4_data_analyzed{filename}.pdf'
    # Check if the file exists, then delete it
    if os.path.exists(pdf_filename):
        os.remove(pdf_filename)
        print(f"{pdf_filename} has been deleted.")
    else:
        print(f"{pdf_filename} does not exist.")

    # Initialize the PDF canvas
    c = canvas.Canvas(pdf_filename, pagesize=letter)
    width, height = letter

    left_margin = 25
    initial_line_height = height - 50
    current_line_height = initial_line_height

    # Write stats to PDF file
    # Adding text to the PDF
    c.setFont("Helvetica", 12)
    c.drawString(left_margin, current_line_height, f"Number of rows using shape: {df.shape[0]}")
    current_line_height -= 20
    c.drawString(left_margin, current_line_height, f"Number of rows using len(): {len(df)}")
    columns = df.columns.tolist()
    current_line_height -= 20
    c.drawString(left_margin, current_line_height, f"Number of columns using len(): {len(columns)}")

    for col in columns:
        if col not in ['publisher','session_traffic_source_last_click','app_info','event_params','privacy_info','user_properties','user_ltv','device','geo','ecommerce','traffic_source','collected_traffic_source','items']:  #These have nested JSON
            # Move to the next page for the next plot and text
            c.showPage()
            current_line_height = initial_line_height
            current_line_height -= 20
            c.drawString(left_margin, current_line_height, f"Column name: {col}")
            # Count of distinct values in 'column_name
            current_line_height -= 20
            c.drawString(left_margin, current_line_height, f"{col} distinct count: {df[col].nunique()}")
            # Count null and non-null values
            null_count = df[col].isnull().sum()
            if null_count > 0:
                non_null_count = df[col].notnull().sum()
                # Create data for the pie chart
                labels = ['Null', 'Non-Null']
                sizes = [null_count, non_null_count]
                colors = ['salmon', 'skyblue']
                # Plot pie chart
                plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
                plt.title(f'{col} Null vs Non-Null values')
                # plt.show()
                # Save plot to a BytesIO object
                plot_buffer = BytesIO()
                plt.savefig(plot_buffer, format='png')
                plt.close()  # Close plot to free memory
                plot_buffer.seek(0)  # Rewind the buffer

                # Draw the plot on the PDF canvas
                current_line_height -= 200
                c.drawImage(ImageReader(plot_buffer), left_margin, current_line_height, width=200, height=150)

            # Plot distribution
            # Get the top most frequent values
            top_values = df[col].value_counts().head(args.top_bucket_size).index
            # Filter the DataFrame to only include these top 100 values
            df_top = df[df[col].isin(top_values)]
            # Sort the unique values by their count in descending order
            df_sorted = df_top[col].value_counts().index
            # Plot count of distinct values in descending order
            sns.countplot(x=col, data=df, order=df_sorted)
            plt.xticks(rotation=45, ha='right')  # Rotate x labels diagonally
            plt.xlabel('Values')
            plt.ylabel('Count')
            plt.title(f'Count of Distinct {col} Values in Descending Order')
            # Apply tight layout to avoid label cutoff
            plt.tight_layout()
            # plt.show()
            # Save plot to a BytesIO object
            plot_buffer = BytesIO()
            plt.savefig(plot_buffer, format='png')
            plt.close()  # Close plot to free memory
            plot_buffer.seek(0)  # Rewind the buffer

            # Draw the plot on the PDF canvas
            current_line_height -= 250
            c.drawImage(ImageReader(plot_buffer), left_margin, current_line_height, width=400, height=300)

    # Save the PDF
    c.save()

    # Example: Query for rows where age is greater than 25 and city is "New York"
    result_df = df.query("event_name == 'page_view'")
    ep_list = result_df["event_params"].tolist()
    print(ep_list)
    one_result = result_df[:1]
    print(one_result)
    one_result["event_params"]

if __name__ == "__main__":
    main()
