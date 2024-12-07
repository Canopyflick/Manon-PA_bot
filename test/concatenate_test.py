import unittest



class ConcatiiTest(unittest.TestCase):
    
    def __init__(self, methodName='runTest'):  
        super().__init__(methodName)  
        
    #Testdata
    def test(self):
        input_1="hoi"
        input_2="doei"
    
        resultaat=concatii(input_1, input_2)
    
        self.assertEqual("hoidoei", resultaat)
if __name__ == "__main__":
    unittest.main()        
    
def concatii(input_1, input_2):
    output = input_1 + input_2
    return output