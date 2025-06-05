import os

base_dir = os.path.dirname(os.path.dirname(__file__))
base_dir = os.path.join(os.path.dirname(base_dir),"data")

position_path = os.path.join(base_dir,'positions')
os.makedirs(position_path,exist_ok = True)


api_key = "MTRrwMPMBIrFJ0Pqgo02MlapNwIXM5PuKHXwsy0ZAd76TXvYdc6AdGKNgTy1UEpA"
secret_key = "jg99TGTGKsE2lvH8m2xnSmNuC0mL2b6RjmeMTFj0GxPVM6sDWK9lgWyG275XqN6m"

