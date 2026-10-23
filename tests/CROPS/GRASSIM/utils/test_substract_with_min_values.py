
def test_subtract_with_min_values():
    from pase.CROPS.GRASSIM.utils.utils import subtract_with_min_values
    import numpy as np

    # Test case 1: 1 compartiment, 3 cells

    arr = np.array([[15, 25, 35]])
    amount = 5
    min_values = [5]

    result = subtract_with_min_values(arr, amount, min_values)
    expected = [np.array([10, 20, 30])]
    assert np.array_equal(result, expected), f"Expected {expected}, but got {result}"

    # Test case 2: 2 compartiments, 3 cells

    arr = np.array([[15, 25, 35], [15, 25, 35]])
    amount = 5
    min_values = [5, 5]

    result = subtract_with_min_values(arr, amount, min_values)
    expected = [np.array([10, 20, 30]), np.array([15, 25, 35])]

    assert np.array_equal(result, expected), f"Expected {expected}, but got {result}"


    # Test case 3: 2 compartiments, 3 cells. Blocked by min values, second compartiment affected in first cell

    arr = np.array([[15, 25, 35], [15, 25, 35]])
    amount = 15
    min_values = [5, 5]

    result = subtract_with_min_values(arr, amount, min_values)
    expected = [np.array([5, 10, 20]), np.array([10, 25, 35])]

    assert np.array_equal(result, expected), f"Expected {expected}, but got {result}"    


    # Test case 4: 2 compartiments, 3 cells. Blocked by min values, second compartiment affected in all cells

    arr = np.array([[15, 25, 35], [15, 25, 35]])
    amount = 35
    min_values = [5, 5]

    result = subtract_with_min_values(arr, amount, min_values)
    expected = [np.array([5, 5, 5]), np.array([5, 10, 30])] 

    assert np.array_equal(result, expected), f"Expected {expected}, but got {result}"  


    # Test case 4: 2 compartiments, 3 cells. initial values lower than min values

    arr = np.array([[15, 25, 35], [15, 25, 35]])
    amount = 35
    min_values = [35, 35]

    result = subtract_with_min_values(arr, amount, min_values)
    expected = [np.array([15, 25, 35]), np.array([15, 25, 35])] 

    assert np.array_equal(result, expected), f"Expected {expected}, but got {result}"  
