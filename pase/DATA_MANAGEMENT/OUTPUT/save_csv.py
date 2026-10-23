import pandas as pd
import numpy as np
import os

def save_mean_to_csv(filename, nyears_data, variables):
    """
    Save the mean values of the variables in the nyears_data dictionary to a CSV file.
    
    Args:
        filename: The name of the CSV file to save.
        filename type: str
        nyears_data: A dictionary containing the data for each year.
        nyears_data type: dict
        variables: A list of variables to save.
        variables type: list
    """
    records = []
    
    for year in nyears_data:
        missing_var = []
        for var in variables:
            if var in nyears_data[year]:  # Ensure the variable exists in the dictionary
                for date, array in nyears_data[year][var].items():
                    mean_value = np.mean(array)
                    records.append((date, var, mean_value))
            else:
                missing_var.append(var)
        if missing_var:
            print(f'Warning: variable(s) {missing_var} not in nyears_data for year {year}')
    
    # Create a DataFrame
    df = pd.DataFrame(records, columns=['Date', 'Variable', 'Mean'])
    df['Date'] = pd.to_datetime(df['Date'])  # Convert to datetime
    df = df.pivot(index='Date', columns='Variable', values='Mean')  # Reshape to have variables as columns
    
    # Save to CSV
    filepath = os.path.join('OUTPUTS', filename)
    df.to_csv(filepath)
    print('saved to', filepath)
