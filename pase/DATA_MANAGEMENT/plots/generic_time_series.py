import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import datetime

def plot_variables(nyears_data_list, variables, start_date, end_date):
    """
    This function is provided as an example and a quick way to plot time series data 
    for mean multiple spatialized variables from multiple datasets within a specified date range.
    
    :param nyears_data_list: A list of dictionaries, each containing yearly data dictionaries.
    :type nyears_Data_list: list
    :param variables: A list of variable names to be plotted.
    :type variables: list 
    :param start_date: The plot start date in the format "YYYY-MM-DD"
    :type start_date: str
    :param start_date: The plot end date in the format "YYYY-MM-DD"
    :type end_date: str
    """
    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    timedelta = end_dt - start_dt
    
    num_vars = len(variables)
    fig, axes = plt.subplots(num_vars, 1, figsize=(12, 6 * num_vars), sharex=False)
    
    if num_vars == 1:
        axes = [axes]
        
    
    for ax, variable in zip(axes, variables):
        dates = []
        values = []
        
        for i, nyears_data in enumerate(nyears_data_list):
            for year, year_dict in nyears_data.items():
                if variable in year_dict:
                    print(f'{variable} found in dict {i}, year {year}')
                    var_dict = year_dict[variable]
                    for date_str, value in var_dict.items():
                        current_dt = datetime.datetime.strptime(str(date_str), "%Y-%m-%d %H:%M:%S")
                        if start_dt <= current_dt <= end_dt:
                            dates.append(current_dt)
                            values.append(np.mean(value))
        
        if not dates:
            ax.set_title(f"No data found for {variable}")
            continue
        
        values = np.array(values)  # Convert to NumPy array in case of multiple dimensions
    
        
        if values.ndim == 1:
            ax.plot(dates, values, label=variable, linewidth='2')
        else:
            for i in range(values.shape[1]):
                ax.plot(dates, values[:, i], label=f"{variable}_{i}")
         
        
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        if timedelta.total_seconds() <= 63072000:
            ax.xaxis.set_minor_locator(mdates.MonthLocator())
            ax.xaxis.set_minor_formatter(mdates.DateFormatter('%m'))
        ax.set_ylabel("Value")
        ax.set_title(f"{variable}")
        ax.legend()
        ax.grid(True)
        ax.tick_params(axis='x', labelrotation=45)
    
    plt.xlabel("Date")
    plt.xticks(rotation=45)
    plt.show()

# Example usage:
# plot_variables([Soil_plot.nyears_data, Crop_plot[0].nyears_data, Crop_plot[1].nyears_data], ['Norg', 'exported_BM'], '2008-01-01', '2009-12-31')
