import numpy as np
import pandas as pd
import pyflux as pf

# Set up some data to use for the tests

noise = np.random.normal(0,1,400)
y = np.zeros(400)
x1 = np.random.normal(0,1,400)
x2 = np.random.normal(0,1,400)

for i in range(1,len(y)):
	y[i] = 0.9*y[i-1] + noise[i] + 0.1*x1[i] - 0.3*x2[i]

data = pd.DataFrame([y,x1,x2]).T
data.columns = ['y', 'x1', 'x2']

y_oos = np.random.normal(0,1,30)
x1_oos = np.random.normal(0,1,30)
x2_oos = np.random.normal(0,1,30)

data_oos = pd.DataFrame([y_oos,x1_oos,x2_oos]).T
data_oos.columns = ['y', 'x1', 'x2']

example_model = pf.GASX(formula="y ~ x1", data=data, ar=1, sc=1, family=pf.GASSkewt())
x = example_model.fit()


def test_skewt_no_terms():
	"""
	Tests the length of the latent variable vector for an GASX model
	with no AR or SC terms, and tests that the values are not nan
	"""
	model = pf.GASX(formula="y ~ x1", data=data, ar=0, sc=0, family=pf.GASSkewt())
	x = model.fit()
	assert(len(model.latent_variables.z_list) == 5)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test_skew_t_model_fit():
	model = pf.GASX(formula="y ~ x1", data=data, ar=1, sc=1, family=pf.GASSkewt())
	x = model.fit()

def test_skewt_couple_terms():
	"""
	Tests the length of the latent variable vector for an GASX model
	with 1 AR and 1 SC term, and tests that the values are not nan
	"""
	assert(len(example_model.latent_variables.z_list) == 7)
	lvs = np.array([i.value for i in example_model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test_skewt_couple_terms_integ():
	"""
	Tests the length of the latent variable vector for an GASX model
	with 1 AR and 1 SC term and integrated once, and tests that the 
	values are not nan
	"""
	model = pf.GASX(formula="y ~ x1", data=data, ar=1, sc=1, integ=1, family=pf.GASSkewt())
	x = model.fit()
	assert(len(model.latent_variables.z_list) == 7)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test_skewt_bbvi():
	"""
	Tests an GASX model estimated with BBVI, and tests that the latent variable
	vector length is correct, and that value are not nan
	"""
	model = pf.GASX(formula="y ~ x1", data=data, ar=1, sc=1, family=pf.GASSkewt())
	x = model.fit('BBVI',iterations=100)
	assert(len(model.latent_variables.z_list) == 7)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test_skewt_mh():
	"""
	Tests an GASX model estimated with Metropolis-Hastings, and tests that the latent variable
	vector length is correct, and that value are not nan
	"""
	model = pf.GASX(formula="y ~ x1", data=data, ar=1, sc=1, family=pf.GASSkewt())
	x = model.fit('M-H',nsims=300)
	assert(len(model.latent_variables.z_list) == 7)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test_skewt_pml():
	"""
	Tests an GASX model estimated with PML, and tests that the latent variable
	vector length is correct, and that value are not nan
	"""
	model = pf.GASX(formula="y ~ x1", data=data, ar=1, sc=1, family=pf.GASSkewt())
	x = model.fit('PML')
	assert(len(model.latent_variables.z_list) == 7)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test_skewt_predict_length():
	"""
	Tests that the length of the predict dataframe is equal to no of steps h
	"""
	assert(example_model.predict(h=5, oos_data=data_oos).shape[0] == 5)

def test_skewt_predict_is_length():
	"""
	Tests that the length of the predict IS dataframe is equal to no of steps h
	"""
	assert(example_model.predict_is(h=5).shape[0] == 5)

""" REACTIVATE TESTS ONCE SKEWT STABILITY SOLUTION IS FOUND
def test_skewt_predict_nans():
	Tests that the predictions are not NaNs
	assert(len(example_model.predict(h=5, oos_data=data_oos).values[np.isnan(example_model.predict(h=5, 
		oos_data=data_oos).values)]) == 0)

def test_skewt_predict_is_nans():
	Tests that the predictions in-sample are not NaNs
	assert(len(example_model.predict_is(h=5).values[np.isnan(example_model.predict_is(h=5).values)]) == 0)
"""

## Try more than one predictor

def test2_skewt_no_terms():
	"""
	Tests the length of the latent variable vector for an GASX model
	with no AR or SC terms, and two predictors, and tests that the values 
	are not nan
	"""
	model = pf.GASX(formula="y ~ x1 + x2", data=data, ar=0, sc=0, family=pf.GASSkewt())
	x = model.fit()
	assert(len(model.latent_variables.z_list) == 6)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test2_skewt_couple_terms():
	"""
	Tests the length of the latent variable vector for an GASX model
	with 1 AR and 1 SC term, and two predictors, and tests that the values 
	are not nan
	"""
	model = pf.GASX(formula="y ~ x1 + x2", data=data, ar=1, sc=1, family=pf.GASSkewt())
	x = model.fit()
	assert(len(model.latent_variables.z_list) == 8)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test2_skewt_bbvi():
	"""
	Tests an GASX model estimated with BBVI, with multiple predictors, and 
	tests that the latent variable vector length is correct, and that value are not nan
	"""
	model = pf.GASX(formula="y ~ x1 + x2", data=data, ar=1, sc=1, family=pf.GASSkewt())
	x = model.fit('BBVI',iterations=100)
	assert(len(model.latent_variables.z_list) == 8)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test2_skewt_mh():
	"""
	Tests an GASX model estimated with MEtropolis-Hastings, with multiple predictors, and 
	tests that the latent variable vector length is correct, and that value are not nan
	"""
	model = pf.GASX(formula="y ~ x1 + x2", data=data, ar=1, sc=1, family=pf.GASSkewt())
	x = model.fit('M-H',nsims=300)
	assert(len(model.latent_variables.z_list) == 8)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test2_skewt_pml():
	"""
	Tests an GASX model estimated with PML, with multiple predictors, and 
	tests that the latent variable vector length is correct, and that value are not nan
	"""
	model = pf.GASX(formula="y ~ x1 + x2", data=data, ar=1, sc=1, family=pf.GASSkewt())
	x = model.fit('PML')
	assert(len(model.latent_variables.z_list) == 8)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test2_skewt_predict_length():
	"""
	Tests that the length of the predict dataframe is equal to no of steps h
	"""
	model = pf.GASX(formula="y ~ x1 + x2", data=data, ar=1, sc=1, family=pf.GASSkewt())
	x = model.fit()
	x.summary()
	assert(model.predict(h=5, oos_data=data_oos).shape[0] == 5)

def test2_skewt_predict_is_length():
	"""
	Tests that the length of the predict IS dataframe is equal to no of steps h
	"""
	model = pf.GASX(formula="y ~ x1 + x2", data=data, ar=1, sc=1, family=pf.GASSkewt())
	x = model.fit()
	assert(model.predict_is(h=5).shape[0] == 5)

