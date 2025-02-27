from PhabrixTools import skip_data

def test_skipdata():
    data = [x for x in range(40)]
    print(data)
    result = skip_data(data)
    print(result)
    assert result[0] == 21
    assert result[-1] == 30

    data = ['0', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '0', '0', '1023', '1023', '577', '263', '278', '264', '512', '515', '512', '277', '767', '767', '767', '767', '512', '512', '719', '512', '512', '20', '512', 
'512', '512', '512', '512', '512', '512', '512', '329', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0']
    result = skip_data(data)
    print(result)
    assert int(result[0]) == 0
    assert int(result[-1]) == 0