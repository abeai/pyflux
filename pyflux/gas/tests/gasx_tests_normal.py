import numpy as np
import pandas as pd
import pyflux as pf

# Set up some data to use for the tests

noise = np.random.normal(0,1,250)
y = np.zeros(250)
x1 = np.random.normal(0,1,250)
x2 = np.random.normal(0,1,250)

for i in range(1,len(y)):
	y[i] = 0.9*y[i-1] + noise[i] + 0.1*x1[i] - 0.3*x2[i]

data = pd.DataFrame([y,x1,x2]).T
data.columns = ['y', 'x1', 'x2']

countdata = np.random.poisson(3,300)
x1 = np.random.normal(0,1,300)
x2 = np.random.normal(0,1,300)
data2 = pd.DataFrame([countdata,x1,x2]).T
data2.columns = ['y', 'x1', 'x2']

y_oos = np.random.normal(0,1,30)
x1_oos = np.random.normal(0,1,30)
x2_oos = np.random.normal(0,1,30)
countdata_oos = np.random.poisson(3,30)

data_oos = pd.DataFrame([y_oos,x1_oos,x2_oos]).T
data_oos.columns = ['y', 'x1', 'x2']

data2_oos = pd.DataFrame([countdata_oos,x1_oos,x2_oos]).T
data2_oos.columns = ['y', 'x1', 'x2']

def test_no_terms():
	"""
	Tests the length of the latent variable vector for an GASX model
	with no AR or SC terms, and tests that the values are not nan
	"""
	model = pf.GASX(formula="y ~ x1", data=data, ar=0, sc=0, family=pf.GASNormal())
	x = model.fit()
	assert(len(model.latent_variables.z_list) == 3)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test_couple_terms():
	"""
	Tests the length of the latent variable vector for an GASX model
	with 1 AR and 1 SC term, and tests that the values are not nan
	"""
	model = pf.GASX(formula="y ~ x1", data=data, ar=1, sc=1, family=pf.GASNormal())
	x = model.fit()
	assert(len(model.latent_variables.z_list) == 5)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test_couple_terms_integ():
	"""
	Tests the length of the latent variable vector for an GASX model
	with 1 AR and 1 SC term and integrated once, and tests that the 
	values are not nan
	"""
	model = pf.GASX(formula="y ~ x1", data=data, ar=1, sc=1, integ=1, family=pf.GASNormal())
	x = model.fit()
	assert(len(model.latent_variables.z_list) == 5)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test_bbvi():
	"""
	Tests an GASX model estimated with BBVI, and tests that the latent variable
	vector length is correct, and that value are not nan
	"""
	model = pf.GASX(formula="y ~ x1", data=data, ar=1, sc=1, family=pf.GASNormal())
	x = model.fit('BBVI',iterations=100)
	assert(len(model.latent_variables.z_list) == 5)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test_mh():
	"""
	Tests an GASX model estimated with Metropolis-Hastings, and tests that the latent variable
	vector length is correct, and that value are not nan
	"""
	model = pf.GASX(formula="y ~ x1", data=data, ar=1, sc=1, family=pf.GASNormal())
	x = model.fit('M-H',nsims=300)
	assert(len(model.latent_variables.z_list) == 5)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test_laplace():
	"""
	Tests an GASX model estimated with Laplace approximation, and tests that the latent variable
	vector length is correct, and that value are not nan
	"""
	model = pf.GASX(formula="y ~ x1", data=data, ar=1, sc=1, family=pf.GASNormal())
	x = model.fit('Laplace')
	assert(len(model.latent_variables.z_list) == 5)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test_pml():
	"""
	Tests an GASX model estimated with PML, and tests that the latent variable
	vector length is correct, and that value are not nan
	"""
	model = pf.GASX(formula="y ~ x1", data=data, ar=1, sc=1, family=pf.GASNormal())
	x = model.fit('PML')
	assert(len(model.latent_variables.z_list) == 5)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test_predict_length():
	"""
	Tests that the length of the predict dataframe is equal to no of steps h
	"""
	model = pf.GASX(formula="y ~ x1", data=data, ar=2, sc=2, family=pf.GASNormal())
	x = model.fit()
	x.summary()
	assert(model.predict(h=5, oos_data=data_oos).shape[0] == 5)

def test_predict_is_length():
	"""
	Tests that the length of the predict IS dataframe is equal to no of steps h
	"""
	model = pf.GASX(formula="y ~ x1", data=data, ar=2, sc=2, family=pf.GASNormal())
	x = model.fit()
	assert(model.predict_is(h=5).shape[0] == 5)

def test_predict_nans():
	"""
	Tests that the predictions are not NaNs
	"""
	model = pf.GASX(formula="y ~ x1", data=data, ar=2, sc=2, family=pf.GASNormal())
	x = model.fit()
	x.summary()
	assert(len(model.predict(h=5, oos_data=data_oos).values[np.isnan(model.predict(h=5, 
		oos_data=data_oos).values)]) == 0)

def test_predict_is_nans():
	"""
	Tests that the predictions in-sample are not NaNs
	"""
	model = pf.GASX(formula="y ~ x1", data=data, ar=2, sc=2, family=pf.GASNormal())
	x = model.fit()
	x.summary()
	assert(len(model.predict_is(h=5).values[np.isnan(model.predict_is(h=5).values)]) == 0)

## Try more than one predictor

def test2_no_terms():
	"""
	Tests the length of the latent variable vector for an GASX model
	with no AR or SC terms, and two predictors, and tests that the values 
	are not nan
	"""
	model = pf.GASX(formula="y ~ x1 + x2", data=data, ar=0, sc=0, family=pf.GASNormal())
	x = model.fit()
	assert(len(model.latent_variables.z_list) == 4)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test2_couple_terms():
	"""
	Tests the length of the latent variable vector for an GASX model
	with 1 AR and 1 SC term, and two predictors, and tests that the values 
	are not nan
	"""
	model = pf.GASX(formula="y ~ x1 + x2", data=data, ar=1, sc=1, family=pf.GASNormal())
	x = model.fit()
	assert(len(model.latent_variables.z_list) == 6)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test2_bbvi():
	"""
	Tests an GASX model estimated with BBVI, with multiple predictors, and 
	tests that the latent variable vector length is correct, and that value are not nan
	"""
	model = pf.GASX(formula="y ~ x1 + x2", data=data, ar=1, sc=1, family=pf.GASNormal())
	x = model.fit('BBVI',iterations=100)
	assert(len(model.latent_variables.z_list) == 6)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test2_mh():
	"""
	Tests an GASX model estimated with MEtropolis-Hastings, with multiple predictors, and 
	tests that the latent variable vector length is correct, and that value are not nan
	"""
	model = pf.GASX(formula="y ~ x1 + x2", data=data, ar=1, sc=1, family=pf.GASNormal())
	x = model.fit('M-H',nsims=300)
	assert(len(model.latent_variables.z_list) == 6)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test2_laplace():
	"""
	Tests an GASX model estimated with Laplace, with multiple predictors, and 
	tests that the latent variable vector length is correct, and that value are not nan
	"""
	model = pf.GASX(formula="y ~ x1 + x2", data=data, ar=1, sc=1, family=pf.GASNormal())
	x = model.fit('Laplace')
	assert(len(model.latent_variables.z_list) == 6)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test2_pml():
	"""
	Tests an GASX model estimated with PML, with multiple predictors, and 
	tests that the latent variable vector length is correct, and that value are not nan
	"""
	model = pf.GASX(formula="y ~ x1 + x2", data=data, ar=1, sc=1, family=pf.GASNormal())
	x = model.fit('PML')
	assert(len(model.latent_variables.z_list) == 6)
	lvs = np.array([i.value for i in model.latent_variables.z_list])
	assert(len(lvs[np.isnan(lvs)]) == 0)

def test2_predict_length():
	"""
	Tests that the length of the predict dataframe is equal to no of steps h
	"""
	model = pf.GASX(formula="y ~ x1 + x2", data=data, ar=1, sc=1, family=pf.GASNormal())
	x = model.fit()
	x.summary()
	assert(model.predict(h=5, oos_data=data_oos).shape[0] == 5)

def test2_predict_is_length():
	"""
	Tests that the length of the predict IS dataframe is equal to no of steps h
	"""
	model = pf.GASX(formula="y ~ x1 + x2", data=data, ar=1, sc=1, family=pf.GASNormal())
	x = model.fit()
	assert(model.predict_is(h=5).shape[0] == 5)

def test2_predict_nans():
	"""
	Tests that the predictions are not NaNs
	"""
	model = pf.GASX(formula="y ~ x1 + x2", data=data, ar=1, sc=1, family=pf.GASNormal())
	x = model.fit()
	x.summary()
	assert(len(model.predict(h=5, oos_data=data_oos).values[np.isnan(model.predict(h=5, 
		oos_data=data_oos).values)]) == 0)

def test2_predict_is_nans():
	"""
	Tests that the predictions in-sample are not NaNs
	"""
	model = pf.GASX(formula="y ~ x1 + x2", data=data, ar=1, sc=1, family=pf.GASNormal())
	x = model.fit()
	x.summary()
	assert(len(model.predict_is(h=5).values[np.isnan(model.predict_is(h=5).values)]) == 0)
