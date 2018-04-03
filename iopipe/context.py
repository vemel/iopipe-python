import decimal
import numbers
import warnings
from . import constants


class ContextWrapper(object):
    def __init__(self, base_context, instance):
        self.base_context = base_context
        self.instance = instance
        self.iopipe = IOpipeContext(self.instance)

    def __getattr__(self, name):
        return getattr(self.base_context, name)


class IOpipeContext(object):
    def __init__(self, instance):
        self.instance = instance

    def metric(self, key, value):
        if self.instance.report is None:
            warnings.warn('Attempting to add metrics before function decorated with IOpipe. '
                          'This metric will not be recorded.')
            return

        name = str(key)
        if len(name) > constants.METRIC_NAME_LIMIT:
            warnings.warn('Custom metric of name %s is longer than allowed limit of '
                          '%s characters. '
                          'This metric will not be recorded.' % (name, constants.METRIC_NAME_LIMIT))
            return

        event = {'name': name}

        # Add numerical values to report
        # We typecast decimals as strings: not JSON serializable and casting to floats can result in rounding errors.
        if isinstance(value, numbers.Number) and not isinstance(value, decimal.Decimal):
            event['n'] = value
        else:
            event['s'] = str(value)

        self.instance.report.custom_metrics.append(event)

    log = metric

    def label(self, name):
        if not isinstance(name, str):
            warnings.warn('Attempted to add a label that is not of type string. '
                          'This label will not be recorded.')
            return

        if len(name) > constants.METRIC_NAME_LIMIT:
            warnings.warn('Label of name %s is longer than allowed limit of '
                          '%s characters. '
                          'This label will not be recorded.' % (name, constants.METRIC_NAME_LIMIT))
            return

        self.instance.report.labels.add(name)

    def error(self, error):
        if self.instance.report is None:
            warnings.warn('An exception occurred before function was decorated with IOpipe. '
                          'This exception will not be recorded.')
            raise error

        self.instance.report.prepare(error)
        self.instance.run_hooks('pre:report')
        self.instance.report.send()
        self.instance.run_hooks('post:report')
        raise error

    def register(self, name, value):
        if not hasattr(self, name):
            setattr(self, name, value)

    def unregister(self, name):
        if hasattr(self, name):
            delattr(self, name)
