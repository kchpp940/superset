# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from flask_babel import lazy_gettext as _

from superset.commands.exceptions import (
    CommandException,
    CommandInvalidError,
    CreateFailedError,
    ForbiddenError,
    ValidationError,
)


class ChartNotFoundValidationError(ValidationError):
    """
    Marshmallow validation error for chart does not exist
    """

    def __init__(self) -> None:
        super().__init__(_("Chart does not exist"), field_name="chart")


class DashboardNotFoundValidationError(ValidationError):
    """
    Marshmallow validation error for dashboard does not exist
    """

    def __init__(self) -> None:
        super().__init__(_("Dashboard does not exist"), field_name="dashboard")


class MetricNotFoundValidationError(ValidationError):
    """
    Marshmallow validation error for metric not found in chart
    """

    def __init__(self, metric: str) -> None:
        super().__init__(
            _('Metric "%(metric)s" not found in chart', metric=metric),
            field_name="metric",
        )


class AnomalyRuleInvalidError(CommandInvalidError):
    status = 422
    message = _("Anomaly Rule parameters are invalid.")


class AnomalyRuleCreateFailedError(CreateFailedError):
    message = _("Anomaly Rule could not be created.")


class AnomalyRuleUpdateFailedError(CreateFailedError):
    message = _("Anomaly Rule could not be updated.")


class AnomalyRuleNotFoundError(CommandException):
    status = 404
    message = _("Anomaly Rule not found.")


class AnomalyRuleDeleteFailedError(CommandException):
    message = _("Anomaly Rule delete failed.")


class AnomalyRuleForbiddenError(ForbiddenError):
    status = 403
    message = _("Access to this anomaly rule is forbidden")


class AnomalyRuleNameUniquenessValidationError(ValidationError):
    """
    Marshmallow validation error for Anomaly Rule name already exists
    """

    def __init__(self, name: str) -> None:
        message = _('An anomaly rule named "%(name)s" already exists', name=name)
        super().__init__([message], field_name="name")


class AnomalyDetectionError(CommandException):
    status = 422
    message = _("Anomaly detection failed.")


class AnomalyDetectionQueryError(CommandException):
    """
    Error when executing query for anomaly detection
    """

    status = 400
    message = _("Error executing query for anomaly detection.")


class AnomalyDetectionTimeoutError(CommandException):
    """
    Timeout during anomaly detection
    """

    status = 408
    message = _("Anomaly detection timed out.")


class AnomalyNotificationError(CommandException):
    """
    Error sending anomaly notification
    """

    status = 422
    message = _("Error sending anomaly notification.")


class AnomalyRuleUnexpectedError(CommandException):
    message = _("Anomaly rule unexpected error")
