import numpy as np

def subtract_with_min_values(input_list, amount, min_values):
    # Ensure the input arrays have the same length and the min_values list matches the number of arrays
    if len(input_list) != len(min_values):
        raise ValueError("The number of arrays in input_list must match the length of min_values.")
    
    n_cells = len(input_list[0])
    
    # Create a copy of the input arrays to avoid modifying the original arrays
    result = [arr.copy() for arr in input_list]
    
    # Loop over each cell (index across all arrays)
    for i in range(n_cells):
        remaining_amount = amount
        
        # Process each value in the cell (each array's corresponding value at index i)
        for j in range(len(input_list)):
            # Calculate how much to subtract from the current value
            if result[j][i] > min_values[j]:
                subtractable_amount = result[j][i] - min_values[j]
                # Determine how much to subtract from this value
                subtract_amount = min(remaining_amount, subtractable_amount)
                result[j][i] -= subtract_amount
                remaining_amount -= subtract_amount
                
                # If the remaining amount is zero, no need to proceed with further subtraction
                if remaining_amount <= 0:
                    break
                
    
    return result