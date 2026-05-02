/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
import { FC, useState, useMemo } from 'react';
import { t } from '@apache-superset/core/translation';
import {
  Label,
  Icons,
  Tooltip,
  Button,
  Modal,
  List,
  Tag,
  Typography,
  Space,
  Divider,
  Descriptions,
} from '@superset-ui/core/components';
import type {
  AnomalyDetection,
  AnomalyRuleType,
  AnomalyDirection,
  AnomalyResult,
} from './types';
import AnomalyRuleConfig from './AnomalyRuleConfig';

const { Text, Title } = Typography;

const getRuleTypeLabel = (ruleType: AnomalyRuleType): string => {
  const labels: Record<AnomalyRuleType, string> = {
    threshold: t('Threshold'),
    mom: t('MOM (Month-Over-Month)'),
    yoy: t('YOY (Year-Over-Year)'),
    period_over_period: t('Period Over Period'),
    consecutive: t('Consecutive Changes'),
  };
  return labels[ruleType] || ruleType;
};

const formatValue = (value: number | undefined): string => {
  if (value === undefined || value === null) return '-';
  return value.toLocaleString(undefined, {
    maximumFractionDigits: 2,
  });
};

const AnomalyDetailModal: FC<{
  visible: boolean;
  onClose: () => void;
  anomalyDetection: AnomalyDetection;
}> = ({ visible, onClose, anomalyDetection }) => {
  const anomalyResults = anomalyDetection?.anomaly_results || [];

  return (
    <Modal
      title={t('Anomaly Detection Results')}
      open={visible}
      onCancel={onClose}
      footer={
        <Button type="primary" onClick={onClose}>
          {t('Close')}
        </Button>
      }
      width={900}
    >
      {anomalyResults.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center' }}>
          <Text type="secondary">{t('No anomaly rules configured for this chart.')}</Text>
        </div>
      ) : (
        <>
          <Descriptions bordered column={4} style={{ marginBottom: '24px' }}>
            <Descriptions.Item label={t('Has Anomaly Rules')}>
              <Tag color="green">{t('Yes')}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('Has Anomalies')}>
              <Tag color={anomalyDetection.has_anomalies ? 'error' : 'success'}>
                {anomalyDetection.has_anomalies ? t('Yes') : t('No')}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('Total Rules')}>
              {anomalyResults.length}
            </Descriptions.Item>
            <Descriptions.Item label={t('Rules With Anomalies')}>
              {anomalyResults.filter(r => r.is_anomaly).length}
            </Descriptions.Item>
          </Descriptions>

          <Divider>{t('Rule Details')}</Divider>

          <List
            dataSource={anomalyResults}
            renderItem={result => (
              <List.Item
                style={{
                  padding: '16px',
                  backgroundColor: result.is_anomaly ? '#fff1f0' : '#f6ffed',
                  borderLeft: `4px solid ${result.is_anomaly ? '#ff4d4f' : '#52c41a'}`,
                  marginBottom: '12px',
                }}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      {result.is_anomaly ? (
                        <Icons.ExclamationCircleOutlined
                          style={{ color: '#ff4d4f', fontSize: '18px' }}
                        />
                      ) : (
                        <Icons.CheckCircleOutlined
                          style={{ color: '#52c41a', fontSize: '18px' }}
                        />
                      )}
                      <Title level={5} style={{ margin: 0 }}>
                        {result.rule_name}
                      </Title>
                      <Tag color={result.is_anomaly ? 'error' : 'success'}>
                        {result.is_anomaly ? t('Anomaly Detected') : t('Normal')}
                      </Tag>
                    </Space>
                  }
                  description={
                    <Space split={<Text type="secondary"> | </Text>}>
                      <Text type="secondary">
                        {t('Metric:')} <Text strong>{result.metric}</Text>
                      </Text>
                      <Text type="secondary">
                        {t('Type:')} <Text strong>{getRuleTypeLabel(result.rule_type)}</Text>
                      </Text>
                      {result.summary && (
                        <>
                          <Text type="secondary">
                            {t('Total Points:')}{' '}
                            <Text strong>{result.summary.total_count}</Text>
                          </Text>
                          <Text type="secondary">
                            {t('Anomalies:')}{' '}
                            <Text strong style={{ color: '#ff4d4f' }}>
                              {result.summary.anomaly_count}
                            </Text>
                          </Text>
                        </>
                      )}
                    </Space>
                  }
                />

                {result.results && result.results.filter(r => r.is_anomaly).length > 0 && (
                  <div style={{ marginTop: '12px' }}>
                    <Text strong>{t('Anomaly Details:')}</Text>
                    <div
                      style={{
                        marginTop: '8px',
                        maxHeight: '200px',
                        overflow: 'auto',
                        padding: '8px',
                        backgroundColor: '#fafafa',
                        borderRadius: '4px',
                      }}
                    >
                      {result.results
                        .filter((r: AnomalyResult) => r.is_anomaly)
                        .slice(0, 10)
                        .map((anomaly: AnomalyResult, index: number) => (
                          <div
                            key={index}
                            style={{
                              padding: '8px',
                              marginBottom: '4px',
                              backgroundColor: '#fff1f0',
                              borderRadius: '4px',
                              fontSize: '12px',
                            }}
                          >
                            <Space split={<Text type="secondary">, </Text>}>
                              {anomaly.row_index !== undefined && (
                                <Text type="secondary">[{t('Row')} {anomaly.row_index + 1}]</Text>
                              )}
                              {anomaly.current_value !== undefined && (
                                <Text>
                                  {t('Value:')} <Text strong>{formatValue(anomaly.current_value)}</Text>
                                </Text>
                              )}
                              {anomaly.change_percent !== undefined && (
                                <Text
                                  style={{
                                    color: anomaly.change_percent > 0 ? '#ff4d4f' : '#52c41a',
                                    fontWeight: 'bold',
                                  }}
                                >
                                  {anomaly.change_percent > 0 ? '+' : ''}
                                  {anomaly.change_percent.toFixed(2)}%
                                </Text>
                              )}
                              {anomaly.threshold_max !== undefined && (
                                <Text type="secondary">
                                  {t('Max:')} {formatValue(anomaly.threshold_max)}
                                </Text>
                              )}
                              {anomaly.threshold_min !== undefined && (
                                <Text type="secondary">
                                  {t('Min:')} {formatValue(anomaly.threshold_min)}
                                </Text>
                              )}
                              {anomaly.message && (
                                <Text type="secondary">{anomaly.message}</Text>
                              )}
                            </Space>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </List.Item>
            )}
          />
        </>
      )}
    </Modal>
  );
};

interface AnomalyBadgeProps {
  anomalyDetection?: AnomalyDetection;
  chartId: number;
  dashboardId?: number;
}

export const AnomalyBadge: FC<AnomalyBadgeProps> = ({
  anomalyDetection,
  chartId,
  dashboardId,
}) => {
  const [showDetail, setShowDetail] = useState(false);
  const [showConfig, setShowConfig] = useState(false);

  const hasAnomalyRules = anomalyDetection?.has_anomaly_rules || false;
  const hasAnomalies = anomalyDetection?.has_anomalies || false;
  const anomalyResults = anomalyDetection?.anomaly_results || [];

  const anomalyCount = anomalyResults.filter(r => r.is_anomaly).length;

  const triggerNode = useMemo(
    () => (
      <Tooltip
        title={
          hasAnomalies
            ? t('Anomalies detected - click to view details')
            : hasAnomalyRules
            ? t('Monitoring active - click to manage rules')
            : t('Configure anomaly detection rules')
        }
      >
        <Label
          icon={
            hasAnomalies ? (
              <Icons.ExclamationCircleOutlined iconSize="m" />
            ) : hasAnomalyRules ? (
              <Icons.CheckCircleOutlined iconSize="m" />
            ) : (
              <Icons.SettingOutlined iconSize="m" />
            )
          }
          className="label"
          type={hasAnomalies ? 'error' : hasAnomalyRules ? 'success' : 'default'}
          onClick={() => {
            if (hasAnomalyRules) {
              setShowDetail(true);
            } else {
              setShowConfig(true);
            }
          }}
        >
          {hasAnomalies
            ? t('Anomaly (%s)', anomalyCount)
            : hasAnomalyRules
            ? t('Normal')
            : t('Configure')}
        </Label>
      </Tooltip>
    ),
    [hasAnomalyRules, hasAnomalies, anomalyCount],
  );

  if (!hasAnomalyRules) {
    return (
      <>
        {triggerNode}
        <AnomalyRuleConfig
          chartId={chartId}
          dashboardId={dashboardId}
          visible={showConfig}
          onClose={() => setShowConfig(false)}
          anomalyDetection={anomalyDetection}
        />
      </>
    );
  }

  return (
    <>
      {triggerNode}
      {anomalyDetection && (
        <AnomalyDetailModal
          visible={showDetail}
          onClose={() => setShowDetail(false)}
          anomalyDetection={anomalyDetection}
        />
      )}
      <AnomalyRuleConfig
        chartId={chartId}
        dashboardId={dashboardId}
        visible={showConfig}
        onClose={() => setShowConfig(false)}
        anomalyDetection={anomalyDetection}
      />
    </>
  );
};

export default AnomalyBadge;
