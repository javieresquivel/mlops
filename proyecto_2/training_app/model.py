from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LinearRegression
import pickle
from .models import ModelType
from sklearn.model_selection import train_test_split
import pandas as pd
from sklearn.metrics import confusion_matrix
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

if __name__ == '__main__':
  print("Model module")


class Model:
  def __init__(self, model_name):
    self.model = None
    self.model_name = model_name
    self.training_data = 0.8 # 80% of the data for training
    self.testing_data = 0.1 # 10% of the data for testing
    self.validation_data = 0.1 # 10% of the data for validation
    self.random_state = 42

  def train(self, X, y):
    # First split off the test set (preserve class balance)
    print("Training model ", self.model_name)
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y,
        test_size=self.testing_data,
        stratify=y,
        random_state=self.random_state
    )
    # Compute validation fraction relative to the temp set
    val_size_rel = self.validation_data / (1 - self.testing_data)
    print("Validation fraction relative to the temp set", val_size_rel)
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp,
        test_size=val_size_rel,
        stratify=y_temp,
        random_state=self.random_state
    )
    print("Training data size", X_train.shape)
    print("Validation data size", X_val.shape)
    print("Testing data size", X_test.shape)
    # Save splits for reuse
    self.X_train, self.X_val, self.X_test = X_train, X_val, X_test
    self.y_train, self.y_val, self.y_test = y_train, y_val, y_test

    match self.model_name:
      case ModelType.RANDOM_FOREST:
        self.model = RandomForestClassifier(n_estimators=300, max_depth=None, random_state=42)
      case ModelType.SVM:
        self.model = SVC(kernel='rbf', C=1.0, gamma='scale', class_weight='balanced', random_state=self.random_state)
      case ModelType.NEURAL_NETWORK:
        print("Training neural network")
        self.model = MLPClassifier(
            hidden_layer_sizes=(50,),
            activation='tanh',
            solver='lbfgs',
            alpha=1e-4,
            max_iter=1000,
            random_state=self.random_state
        )
      case _:
        raise ValueError(f"Model type {self.model_name} not supported")

    self.model.fit(X_train, y_train)
    # Store validation score for convenience
    self.val_score_ = self.model.score(X_val, y_val)
  #end of train

  def save(self, model_path):
    with open(model_path, 'wb') as f: # save the model to the file
      pickle.dump(self.model, f)
  #end of save

  def load(self, model_path):
    with open(model_path, 'rb') as f: # load the model from the file
      self.model = pickle.load(f)
  #end of load

  def evaluate(self, X, y):
    return self.model.score(X, y)

  def evaluate_train(self):
    return self.model.score(self.X_train, self.y_train)

  def evaluate_val(self):
    return self.model.score(self.X_val, self.y_val)

  def evaluate_test(self):
    return self.model.score(self.X_test, self.y_test)

  def _confusion_matrix(self, X, y, as_dataframe: bool = False):
      # Only valid for classification models
      if not hasattr(self.model, "classes_"):
          raise ValueError("Confusion matrix is only available for classification models.")
      y_pred = self.model.predict(X)
      cm = confusion_matrix(y, y_pred)
      if as_dataframe:
          labels = list(self.model.classes_)
          return pd.DataFrame(cm, index=labels, columns=labels)
      return cm

  def confusion_matrix_train(self, as_dataframe: bool = False):
      return self._confusion_matrix(self.X_train, self.y_train, as_dataframe)

  def confusion_matrix_val(self, as_dataframe: bool = False):
      return self._confusion_matrix(self.X_val, self.y_val, as_dataframe)

  def confusion_matrix_test(self, as_dataframe: bool = False):
      return self._confusion_matrix(self.X_test, self.y_test, as_dataframe)

  def classification_metrics(self, X, y):
      """Return accuracy, precision, recall, and F1 macro for the given set."""
      y_pred = self.model.predict(X)
      return {
          'accuracy': accuracy_score(y, y_pred),
          'precision_macro': precision_score(y, y_pred, average='macro', zero_division=0),
          'recall_macro': recall_score(y, y_pred, average='macro', zero_division=0),
          'f1_macro': f1_score(y, y_pred, average='macro', zero_division=0)
      }

  def metrics_train(self):
      return self.classification_metrics(self.X_train, self.y_train)

  def metrics_val(self):
      return self.classification_metrics(self.X_val, self.y_val)

  def metrics_test(self):
      return self.classification_metrics(self.X_test, self.y_test)
  def get_model(self):
    return self.model
  


  def predict(self, X):
    return self.model.predict(X)