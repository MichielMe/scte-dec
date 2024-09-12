from PhabrixTools import skip_data

def test_skipdata():
    data = [x for x in range(40)]
    print(data)
    result = skip_data(data)
    print(result)
    assert result[0] == 23
    assert result[-1] == 30
