import sys
if sys.version_info < (3,):
    range = xrange

import numpy as np
import pandas as pd
import scipy.stats as ss
import scipy.special as sp
import seaborn as sns
from patsy import dmatrices, dmatrix, demo_data

from .. import inference as ifr
from .. import tsm as tsm
from .. import distributions as dst
from .. import data_check as dc

from .gasmodels import *

from .gas_recursions import gasx_recursion

class GASX(tsm.TSM):
    """ Inherits time series methods from TSM class.

    **** GENERALIZED AUTOREGRESSIVE SCORE E(X)OGENOUS VARIABLE (GASX) MODELS ****

    Parameters
    ----------
    data : pd.DataFrame or np.array
        Field to specify the time series data that will be used.

    formula : string
        patsy string describing the regression

    ar : int
        Field to specify how many AR lags the model will have.

    sc : int
        Field to specify how many score lags terms the model will have.

    integ : int (default : 0)
        Specifies how many time to difference the time series.

    dist : str
        Which distribution to use
    """

    def __init__(self, data, formula, ar, sc, family, integ=0):

        # Initialize TSM object     
        super(GASX,self).__init__('GASX')

        self.ar = ar
        self.sc = sc
        self.integ = integ
        self.z_no = self.ar + self.sc
        self.max_lag = max(self.ar,self.sc)
        self._z_hide = 0 # Whether to cutoff variance latent variables from results
        self.supported_methods = ["MLE","PML","Laplace","M-H","BBVI"]
        self.default_method = "MLE"
        self.multivariate_model = False

        # Format the data
        self.is_pandas = True # This is compulsory for this model type
        self.data_original = data.copy()
        self.formula = formula
        self.y, self.X = dmatrices(formula, data)
        self.y_name = self.y.design_info.describe()
        self.X_names = self.X.design_info.describe().split(" + ")
        self.y = self.y.astype(np.float) 
        self.X = self.X.astype(np.float) 
        self.param_no = self.X.shape[1]
        self.data_name = self.y_name
        self.y = np.array([self.y]).ravel()
        self.data = self.y.copy()
        self.X = np.array([self.X])[0]
        self.index = data.index

        # Difference data
        for order in range(0,self.integ):
            self.y = np.diff(self.y)
            self.data = np.diff(self.data)
            self.data_name = "Differenced " + self.data_name

        self._create_model_matrices()
        self._create_latent_variables()

        self.family = family
        
        self.model_name2, self.link, self.scale, self.shape, self.skewness, self.mean_transform, self.cythonized = self.family.setup()

        # Identify whether model has cythonized backend - then choose update type
        if self.cythonized is True:
            self._model = self._cythonized_model
            if self.family.gradient_only is True:
                self.recursion = self.family.gradientx_recursion()
            else:
                self.recursion = self.family.newtonx_recursion()
        else:
            self._model = self._uncythonized_model

        self.model_name = self.model_name2 + "X(" + str(self.ar) + "," + str(self.integ) + "," + str(self.sc) + ")"

        # Build any remaining latent variables that are specific to the family chosen
        for no, i in enumerate(self.family.build_latent_variables()):
            self.latent_variables.add_z(i[0],i[1],i[2])
            self.latent_variables.z_list[no+self.ar+self.sc+self.X.shape[1]].start = i[3]

        self.latent_variables.z_list[0].start = self.mean_transform(np.mean(self.data))
        self.z_no = len(self.latent_variables.z_list)
        
    def _create_model_matrices(self):
        """ Creates model matrices/vectors

        Returns
        ----------
        None (changes model attributes)
        """

        self.model_Y = np.array(self.data[self.max_lag:self.data.shape[0]])
        self.model_scores = np.zeros(self.model_Y.shape[0])

    def _create_latent_variables(self):
        """ Creates model latent variables

        Returns
        ----------
        None (changes model attributes)
        """

        for ar_term in range(self.ar):
            self.latent_variables.add_z('AR(' + str(ar_term+1) + ')',ifr.Normal(0,0.5,transform=None),dst.q_Normal(0,3))

        for sc_term in range(self.sc):
            self.latent_variables.add_z('SC(' + str(sc_term+1) + ')',ifr.Normal(0,0.5,transform=None),dst.q_Normal(0,3))

        for parm in range(len(self.X_names)):
            self.latent_variables.add_z('Beta ' + self.X_names[parm],ifr.Normal(0,3,transform=None),dst.q_Normal(0,3))

    def _get_scale_and_shape(self, parm):
        """ Obtains appropriate model scale and shape latent variables

        Parameters
        ----------
        parm : np.array
            Transformed latent variable vector

        Returns
        ----------
        None (changes model attributes)
        """

        if self.scale is True:
            if self.shape is True:
                model_shape = parm[-1]  
                model_scale = parm[-2]
            else:
                model_shape = 0
                model_scale = parm[-1]
        else:
            model_scale = 0
            model_shape = 0 

        if self.skewness is True:
            model_skewness = parm[-3]
        else:
            model_skewness = 0

        return model_scale, model_shape, model_skewness

    def _cythonized_model(self, beta):
        """ Creates the structure of the model

        Parameters
        ----------
        beta : np.array
            Contains untransformed starting values for latent variables

        Returns
        ----------
        theta : np.array
            Contains the predicted values for the time series

        Y : np.array
            Contains the length-adjusted time series (accounting for lags)

        scores : np.array
            Contains the scores for the time series
        """

        parm = np.array([self.latent_variables.z_list[k].prior.transform(beta[k]) for k in range(beta.shape[0])])
        model_scale, model_shape, model_skewness = self._get_scale_and_shape(parm)
        theta = np.matmul(self.X[self.integ+self.max_lag:],parm[self.sc+self.ar:(self.sc+self.ar+len(self.X_names))])

        # Loop over time series
        theta, self.model_scores = self.recursion(parm, theta, self.model_scores, self.model_Y, self.ar, self.sc, self.model_Y.shape[0], model_scale, model_shape, model_skewness, self.max_lag)

        return theta, self.model_Y, self.model_scores

    def _uncythonized_model(self, beta):
        """ Creates the structure of the model

        Parameters
        ----------
        beta : np.array
            Contains untransformed starting values for latent variables

        Returns
        ----------
        theta : np.array
            Contains the predicted values for the time series

        Y : np.array
            Contains the length-adjusted time series (accounting for lags)

        scores : np.array
            Contains the scores for the time series
        """

        parm = np.array([self.latent_variables.z_list[k].prior.transform(beta[k]) for k in range(beta.shape[0])])
        model_scale, model_shape, model_skewness = self._get_scale_and_shape(parm)
        theta = np.matmul(self.X[self.integ+self.max_lag:],parm[self.sc+self.ar:(self.sc+self.ar+len(self.X_names))])

        # Loop over time series
        theta, self.model_scores = gasx_recursion(parm, theta, self.model_scores, self.model_Y, self.ar, self.sc, self.model_Y.shape[0], self.family.score_function, 
            self.link, model_scale, model_shape, model_skewness, self.max_lag)

        return theta, self.model_Y, self.model_scores

    def _mean_prediction(self, theta, Y, scores, h, t_params, X_oos):
        """ Creates a h-step ahead mean prediction

        Parameters
        ----------
        theta : np.array
            The past predicted values

        Y : np.array
            The past data

        scores : np.array
            The past scores

        h : int
            How many steps ahead for the prediction

        t_params : np.array
            A vector of (transformed) latent variables

        X_oos : np.array
            Out of sample X data

        Returns
        ----------
        Y_exp : np.array
            Vector of past values and predictions 
        """     

        Y_exp = Y.copy()
        theta_exp = theta.copy()
        scores_exp = scores.copy()

        #(TODO: vectorize the inner construction here)      
        for t in range(0,h):
            new_value = t_params[0]

            if self.ar != 0:
                for j in range(1,self.ar+1):
                    new_value += t_params[j]*theta_exp[-j]
            if self.sc != 0:
                for k in range(1,self.sc+1):
                    new_value += t_params[k+self.ar]*scores_exp[-k]

            new_value += np.matmul(X_oos[t,:],t_params[self.sc+self.ar:(self.sc+self.ar+len(self.X_names))])            

            if self.model_name2 == "Exponential GAS":
                Y_exp = np.append(Y_exp,[1.0/self.link(new_value)])
            else:
                Y_exp = np.append(Y_exp,[self.link(new_value)])
            theta_exp = np.append(theta_exp,[new_value]) # For indexing consistency
            scores_exp = np.append(scores_exp,[0]) # expectation of score is zero

        return Y_exp

    def _preoptimize_model(self, initials, method):
        """ Preoptimizes the model by estimating a static model, then a quick search of good dynamic parameters

        Parameters
        ----------
        initials : np.array
            A vector of inital values

        method : str
            One of 'MLE' or 'PML' (the optimization options)

        Returns
        ----------
        Y_exp : np.array
            Vector of past values and predictions 
        """
        if not (self.ar==0 and self.sc == 0):
            toy_model = GASX(formula=self.formula, ar=0, sc=0, integ=self.integ, family=self.family, data=self.data_original)
            toy_model.fit(method)
            self.latent_variables.z_list[0].start = toy_model.latent_variables.get_z_values(transformed=False)[0]
            
            for extra_z in range(len(self.family.build_latent_variables())):
                self.latent_variables.z_list[self.ar+self.sc+extra_z].start = toy_model.latent_variables.get_z_values(transformed=False)[extra_z]
            
            # Random search for good AR/SC starting values
            random_starts = np.random.normal(0.3, 0.3, [self.ar+self.sc+len(self.X_names), 1000])

            best_start = self.latent_variables.get_z_starting_values()
            best_lik = self.neg_loglik(self.latent_variables.get_z_starting_values())
            proposal_start = best_start.copy()

            for start in range(random_starts.shape[1]):
                proposal_start[:self.ar+self.sc+len(self.X_names)] = random_starts[:,start]
                proposal_start[0] = proposal_start[0]*(1.0-np.sum(random_starts[:self.ar,start]))
                proposal_likelihood = self.neg_loglik(proposal_start)
                if proposal_likelihood < best_lik:
                    best_lik = proposal_likelihood
                    best_start = proposal_start.copy()

            return best_start

        else:
            return initials

    def _sim_prediction(self, theta, Y, scores, h, t_params, X_oos, simulations):
        """ Simulates a h-step ahead mean prediction

        Parameters
        ----------
        theta : np.array
            The past predicted values

        Y : np.array
            The past data

        scores : np.array
            The past scores

        h : int
            How many steps ahead for the prediction

        t_params : np.array
            A vector of (transformed) latent variables

        X_oos : np.array
            Out of sample X data

        simulations : int
            How many simulations to perform

        Returns
        ----------
        Matrix of simulations
        """     

        model_scale, model_shape, model_skewness = self._get_scale_and_shape(t_params)

        sim_vector = np.zeros([simulations,h])

        for n in range(0,simulations):
            Y_exp = Y.copy()
            theta_exp = theta.copy()
            scores_exp = scores.copy()

            #(TODO: vectorize the inner construction here)  
            for t in range(0, h):
                new_value = t_params[0]

                if self.ar != 0:
                    for j in range(1, self.ar+1):
                        new_value += t_params[j]*theta_exp[-j]

                if self.sc != 0:
                    for k in range(1, self.sc+1):
                        new_value += t_params[k+self.ar]*scores_exp[-k]

                new_value += np.matmul(X_oos[t,:],t_params[self.sc+self.ar:(self.sc+self.ar+len(self.X_names))])            

                if self.model_name2 == "Exponential GAS":
                    rnd_value = self.family.draw_variable(1.0/self.link(new_value),model_scale,model_shape,model_skewness,1)[0]
                else:
                    rnd_value = self.family.draw_variable(self.link(new_value),model_scale,model_shape,model_skewness,1)[0]

                Y_exp = np.append(Y_exp,[rnd_value])
                theta_exp = np.append(theta_exp,[new_value]) # For indexing consistency
                scores_exp = np.append(scores_exp,scores[np.random.randint(scores.shape[0])]) # expectation of score is zero

            sim_vector[n] = Y_exp[-h:]

        return np.transpose(sim_vector)


    def _summarize_simulations(self, mean_values, sim_vector, date_index, h, past_values):
        """ Summarizes a simulation vector and a mean vector of predictions

        Parameters
        ----------
        mean_values : np.array
            Mean predictions for h-step ahead forecasts

        sim_vector : np.array
            N simulation predictions for h-step ahead forecasts

        date_index : pd.DateIndex or np.array
            Dates for the simulations

        h : int
            How many steps ahead are forecast

        past_values : int
            How many past observations to include in the forecast plot

        intervals : Boolean
            Would you like to show prediction intervals for the forecast?
        """ 

        error_bars = []
        for pre in range(5,100,5):
            error_bars.append(np.insert([np.percentile(i,pre) for i in sim_vector] - mean_values[(mean_values.shape[0]-h):(mean_values.shape[0])],0,0))
        forecasted_values = mean_values[-h-1:]
        plot_values = mean_values[-h-past_values:]
        plot_index = date_index[-h-past_values:]
        return error_bars, forecasted_values, plot_values, plot_index

    def neg_loglik(self, beta):
        """ Returns the negative loglikelihood of the model

        Parameters
        ----------
        beta : np.array
            Contains untransformed starting values for latent variables
        """
        theta, Y, _ = self._model(beta)
        parm = np.array([self.latent_variables.z_list[k].prior.transform(beta[k]) for k in range(beta.shape[0])])
        model_scale, model_shape, model_skewness = self._get_scale_and_shape(parm)
        return self.family.neg_loglikelihood(Y,self.link(theta),model_scale,model_shape,model_skewness)

    def plot_fit(self, intervals=False, **kwargs):
        """ Plots the fit of the model

        Returns
        ----------
        None (plots data and the fit)
        """
        import matplotlib.pyplot as plt

        figsize = kwargs.get('figsize',(10,7))

        if self.latent_variables.estimated is False:
            raise Exception("No latent variables estimated!")
        else:
            date_index = self.index[max(self.ar,self.sc):]
            mu, Y, scores = self._model(self.latent_variables.get_z_values())
            plt.figure(figsize=figsize)
            plt.subplot(2,1,1)
            plt.title("Model fit for " + self.data_name)

            # Catch specific family properties (imply different link functions/moments)
            if self.model_name2 == "Exponential GAS":
                values_to_plot = 1.0/self.link(mu)
            elif self.model_name2 == "Skewt GAS":
                t_params = self.transform_z()
                model_scale, model_shape, model_skewness = self._get_scale_and_shape(t_params)
                m1 = (np.sqrt(model_shape)*sp.gamma((model_shape-1.0)/2.0))/(np.sqrt(np.pi)*sp.gamma(model_shape/2.0))
                additional_loc = (model_skewness - (1.0/model_skewness))*model_scale*m1
                values_to_plot = mu + additional_loc
            else:
                values_to_plot = self.link(mu)

            plt.plot(date_index,Y,label='Data')
            plt.plot(date_index,values_to_plot,label='GAS Filter',c='black')
            plt.legend(loc=2)   

            plt.subplot(2,1,2)
            plt.title("Filtered values for " + self.data_name)
            plt.plot(date_index,values_to_plot,label='GAS Filter',c='black')
            plt.legend(loc=2)   

            plt.show()              
    
    def plot_predict(self, h=5, past_values=20, intervals=True, oos_data=None, **kwargs):
        """ Makes forecast with the estimated model

        Parameters
        ----------
        h : int (default : 5)
            How many steps ahead would you like to forecast?

        past_values : int (default : 20)
            How many past observations to show on the forecast graph?

        intervals : Boolean
            Would you like to show prediction intervals for the forecast?

        oos_data : pd.DataFrame
            Data for the variables to be used out of sample (ys can be NaNs)

        Returns
        ----------
        - Plot of the forecast
        """
        import matplotlib.pyplot as plt

        figsize = kwargs.get('figsize',(10,7))

        if self.latent_variables.estimated is False:
            raise Exception("No latent variables estimated!")
        else:
            # Sort/manipulate the out-of-sample data
            _, X_oos = dmatrices(self.formula, oos_data)
            X_oos = np.array([X_oos])[0]
            X_pred = X_oos[:h]

            # Retrieve data, dates and (transformed) latent variables
            theta, Y, scores = self._model(self.latent_variables.get_z_values())          
            date_index = self.shift_dates(h)
            t_params = self.transform_z()

            # Get mean prediction and simulations (for errors)
            mean_values = self._mean_prediction(theta,Y,scores,h,t_params,X_pred)

            if self.model_name2 == "Skewt GAS":
                model_scale, model_shape, model_skewness = self._get_scale_and_shape(t_params)
                m1 = (np.sqrt(model_shape)*sp.gamma((model_shape-1.0)/2.0))/(np.sqrt(np.pi)*sp.gamma(model_shape/2.0))
                mean_values += (model_skewness - (1.0/model_skewness))*model_scale*m1 

            sim_values = self._sim_prediction(theta,Y,scores,h,t_params,X_pred,15000)
            error_bars, forecasted_values, plot_values, plot_index = self._summarize_simulations(mean_values,sim_values,date_index,h,past_values)
            plt.figure(figsize=figsize)
            if intervals == True:
                alpha =[0.15*i/float(100) for i in range(50,12,-2)]
                for count, pre in enumerate(error_bars):
                    plt.fill_between(date_index[-h-1:], forecasted_values-pre, forecasted_values+pre,
                        alpha=alpha[count])         
            
            plt.plot(plot_index,plot_values)
            plt.title("Forecast for " + self.data_name)
            plt.xlabel("Time")
            plt.ylabel(self.data_name)
            plt.show()

    def predict_is(self, h=5, fit_once=True):
        """ Makes dynamic in-sample predictions with the estimated model

        Parameters
        ----------
        h : int (default : 5)
            How many steps would you like to forecast?

        fit_once : boolean
            (default: True) Fits only once before the in-sample prediction; if False, fits after every new datapoint

        Returns
        ----------
        - pd.DataFrame with predicted values
        """     

        predictions = []

        for t in range(0,h):
            data1 = self.data_original.iloc[:-(h+t),:]
            data2 = self.data_original.iloc[-h+t:,:]
            x = GASX(ar=self.ar,sc=self.sc,formula=self.formula,integ=self.integ,family=self.family,data=self.data_original[:-h+t])
            
            if fit_once is False:
                x.fit(printer=False)
            if t == 0:
                if fit_once is True:
                    x.fit(printer=False)
                    saved_lvs = x.latent_variables
                predictions = x.predict(1, oos_data=data2)
            else:
                if fit_once is True:
                    x.latent_variables = saved_lvs
                predictions = pd.concat([predictions,x.predict(h=1, oos_data=data2)])
    
        predictions.rename(columns={0:self.y_name}, inplace=True)
        predictions.index = self.index[-h:]

        return predictions

    def plot_predict_is(self, h=5, fit_once=True, **kwargs):
        """ Plots forecasts with the estimated model against data
            (Simulated prediction with data)

        Parameters
        ----------
        h : int (default : 5)
            How many steps to forecast

        fit_once : boolean
            (default: True) Fits only once before the in-sample prediction; if False, fits after every new datapoint

        Returns
        ----------
        - Plot of the forecast against data 
        """
        import matplotlib.pyplot as plt

        figsize = kwargs.get('figsize',(10,7))

        plt.figure(figsize=figsize)
        predictions = self.predict_is(h, fit_once=fit_once)
        data = self.data[-h:]

        plt.plot(predictions.index,data,label='Data')
        plt.plot(predictions.index,predictions,label='Predictions',c='black')
        plt.title(self.data_name)
        plt.legend(loc=2)   
        plt.show()          

    def predict(self,h=5, oos_data=None):
        """ Makes forecast with the estimated model

        Parameters
        ----------
        h : int (default : 5)
            How many steps ahead would you like to forecast?

        oos_data : pd.DataFrame
            Data for the variables to be used out of sample (ys can be NaNs)

        Returns
        ----------
        - pd.DataFrame with predicted values
        """     

        if self.latent_variables.estimated is False:
            raise Exception("No latent variables estimated!")
        else:
            # Sort/manipulate the out-of-sample data
            _, X_oos = dmatrices(self.formula, oos_data)
            X_oos = np.array([X_oos])[0]
            X_pred = X_oos[:h]
            theta, Y, scores = self._model(self.latent_variables.get_z_values())          
            date_index = self.shift_dates(h)
            t_params = self.transform_z()

            mean_values = self._mean_prediction(theta,Y,scores,h,t_params,X_pred)
            if self.model_name2 == "Skewt GAS":
                model_scale, model_shape, model_skewness = self._get_scale_and_shape(t_params)
                m1 = (np.sqrt(model_shape)*sp.gamma((model_shape-1.0)/2.0))/(np.sqrt(np.pi)*sp.gamma(model_shape/2.0))
                forecasted_values = mean_values[-h:] + (model_skewness - (1.0/model_skewness))*model_scale*m1 
            else:
                forecasted_values = mean_values[-h:] 
                
            result = pd.DataFrame(forecasted_values)
            result.rename(columns={0:self.data_name}, inplace=True)
            result.index = date_index[-h:]

            return result