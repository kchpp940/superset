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
import { FC, useState, useEffect, useCallback, useMemo } from 'react';
import {
  Form,
  Input,
  InputNumber,
  Select,
  Radio,
  Card,
  Row,
  Col,
  Button,
  message,
  Typography,
  Space,
  Divider,
  List,
  Popconfirm,
  Tooltip,
  Tag,
  Modal,
  Tabs,
} from '@superset-ui/core/components';
import { t } from '@apache-superset/core/translation';
import { useSelector } from 'react-redux';
import type { RootState } from 'src/dashboard/types';
import type {
  AnomalyRule,
  AnomalyRuleType,
  AnomalyDirection,
  AnomalyRuleStatus,
  AnomalyRuleRequest,
  AnomalyDetection,
} from './types';
import {
  getAnomalyRules,
  createAnomalyRule,
  updateAnomalyRule,
  deleteAnomalyRule,
} from './api';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;
const { TabPane } = Tabs;

interface AnomalyRuleConfigProps {
  chartId: number;
  dashboardId?: number;
  visible: boolean;
  onClose: () => void;
  anomalyDetection?: AnomalyDetection;
}

const RULE_TYPE_OPTIONS = [
  { value: 'threshold', label: t('Threshold Alert') },
  { value: 'mom', label: t('Month-Over-Month (MOM)') },
  { value: 'yoy', label: t('Year-Over-Year (YOY)') },
  { value: 'period_over_period', label: t('Custom Period Over Period') },
  { value: 'consecutive', label: t('Consecutive N Changes') },
];

const DIRECTION_OPTIONS = [
  { value: 'increase', label: t('Increase Only') },
  { value: 'decrease', label: t('Decrease Only') },
  { value: 'both', label: t('Both Increase and Decrease') },
];

const AnomalyRuleList: FC<{
  rules: AnomalyRule[];
  onEdit: (rule: AnomalyRule) => void;
  onDelete: (id: number) => void;
}> = ({ rules, onEdit, onDelete }) => {
  if (rules.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <Text type="secondary">{t('No anomaly rules configured yet.')}</Text>
        <br />
        <Text type="secondary">{t('Create a new rule to get started.')}</Text>
      </div>
    );
  }

  const getRuleTypeLabel = (type: AnomalyRuleType) => {
    const option = RULE_TYPE_OPTIONS.find(o => o.value === type);
    return option ? option.label : type;
  };

  return (
    <List
      dataSource={rules}
      renderItem={rule => (
        <List.Item
          actions={[
            <Button type="link" onClick={() => onEdit(rule)}>
              {t('Edit')}
            </Button>,
            <Popconfirm
              title={t('Are you sure you want to delete this rule?')}
              onConfirm={() => onDelete(rule.id)}
              okText={t('Yes')}
              cancelText={t('No')}
            >
              <Button type="link" danger>
                {t('Delete')}
              </Button>
            </Popconfirm>,
          ]}
        >
          <List.Item.Meta
            title={
              <Space>
                <Text strong>{rule.name}</Text>
                <Tag color={rule.status === 'active' ? 'green' : 'default'}>
                  {rule.status === 'active' ? t('Active') : t('Inactive')}
                </Tag>
                {rule.last_anomaly_at && (
                  <Tag color="warning">{t('Has anomalies')}</Tag>
                )}
              </Space>
            }
            description={
              <Space split={<Text type="secondary"> | </Text>}>
                <Text type="secondary">
                  {t('Metric:')} <Text strong>{rule.metric}</Text>
                </Text>
                <Text type="secondary">
                  {t('Type:')} <Text strong>{getRuleTypeLabel(rule.rule_type)}</Text>
                </Text>
                {rule.description && (
                  <Text type="secondary">{rule.description}</Text>
                )}
              </Space>
            }
          />
        </List.Item>
      )}
    />
  );
};

const AnomalyRuleForm: FC<{
  chartId: number;
  dashboardId?: number;
  editingRule: AnomalyRule | null;
  onSubmit: (values: Record<string, unknown>) => void;
  onCancel: () => void;
  loading: boolean;
}> = ({ chartId, dashboardId, editingRule, onSubmit, onCancel, loading }) => {
  const [form] = Form.useForm();
  const [ruleType, setRuleType] = useState<AnomalyRuleType>(
    (editingRule?.rule_type || 'threshold') as AnomalyRuleType,
  );

  useEffect(() => {
    if (editingRule) {
      form.setFieldsValue({
        name: editingRule.name,
        description: editingRule.description,
        metric: editingRule.metric,
        rule_type: editingRule.rule_type,
        status: editingRule.status,
        ...(editingRule.rule_config as Record<string, unknown>),
      });
      setRuleType(editingRule.rule_type);
    } else {
      form.resetFields();
      setRuleType('threshold' as AnomalyRuleType);
    }
  }, [editingRule, form]);

  const handleValuesChange = (changedValues: Record<string, unknown>) => {
    if (changedValues.rule_type) {
      setRuleType(changedValues.rule_type as AnomalyRuleType);
    }
  };

  const renderRuleConfigFields = () => {
    switch (ruleType) {
      case 'threshold':
        return (
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="threshold_max"
                label={t('Max Threshold')}
                tooltip={t('Alert when value exceeds this threshold')}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder={t('Enter max threshold')}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="threshold_min"
                label={t('Min Threshold')}
                tooltip={t('Alert when value is below this threshold')}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder={t('Enter min threshold')}
                />
              </Form.Item>
            </Col>
          </Row>
        );

      case 'mom':
      case 'yoy':
        return (
          <>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="change_percent"
                  label={t('Change Percent (%)')}
                  rules={[
                    { required: true, message: t('Please enter change percent threshold') },
                  ]}
                  tooltip={t('Alert when change percentage exceeds this value')}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    max={1000}
                    placeholder={t('e.g., 10 for 10%')}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="change_absolute"
                  label={t('Absolute Change (Optional)')}
                  tooltip={t('Optional: Alert when absolute change exceeds this value')}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    placeholder={t('Enter absolute change')}
                  />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item
              name="direction"
              label={t('Direction')}
              rules={[{ required: true, message: t('Please select direction') }]}
              initialValue="both"
            >
              <Radio.Group>
                {DIRECTION_OPTIONS.map(opt => (
                  <Radio key={opt.value} value={opt.value}>
                    {opt.label}
                  </Radio>
                ))}
              </Radio.Group>
            </Form.Item>
          </>
        );

      case 'period_over_period':
        return (
          <>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="period_offset"
                  label={t('Period Offset')}
                  rules={[{ required: true, message: t('Please enter period offset') }]}
                  tooltip={t('Number of periods to compare (e.g., 7 for weekly comparison)')}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={1}
                    placeholder={t('e.g., 7')}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="change_percent"
                  label={t('Change Percent (%)')}
                  rules={[
                    { required: true, message: t('Please enter change percent threshold') },
                  ]}
                  tooltip={t('Alert when change percentage exceeds this value')}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    max={1000}
                    placeholder={t('e.g., 10 for 10%')}
                  />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item
              name="change_absolute"
              label={t('Absolute Change (Optional)')}
              tooltip={t('Optional: Alert when absolute change exceeds this value')}
            >
              <InputNumber style={{ width: '100%' }} placeholder={t('Enter absolute change')} />
            </Form.Item>
            <Form.Item
              name="direction"
              label={t('Direction')}
              rules={[{ required: true, message: t('Please select direction') }]}
              initialValue="both"
            >
              <Radio.Group>
                {DIRECTION_OPTIONS.map(opt => (
                  <Radio key={opt.value} value={opt.value}>
                    {opt.label}
                  </Radio>
                ))}
              </Radio.Group>
            </Form.Item>
          </>
        );

      case 'consecutive':
        return (
          <>
            <Form.Item
              name="consecutive_count"
              label={t('Consecutive Count (N)')}
              rules={[{ required: true, message: t('Please enter consecutive count') }]}
              tooltip={t('Alert when value changes consecutively N times')}
            >
              <InputNumber
                style={{ width: '100%' }}
                min={2}
                max={20}
                placeholder={t('e.g., 3 for 3 consecutive changes')}
              />
            </Form.Item>
            <Form.Item
              name="direction"
              label={t('Direction')}
              rules={[{ required: true, message: t('Please select direction') }]}
              initialValue="both"
            >
              <Radio.Group>
                {DIRECTION_OPTIONS.map(opt => (
                  <Radio key={opt.value} value={opt.value}>
                    {opt.label}
                  </Radio>
                ))}
              </Radio.Group>
            </Form.Item>
          </>
        );

      default:
        return null;
    }
  };

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={onSubmit}
      onValuesChange={handleValuesChange}
      initialValues={{
        status: 'active' as AnomalyRuleStatus,
        rule_type: 'threshold' as AnomalyRuleType,
      }}
    >
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            name="name"
            label={t('Rule Name')}
            rules={[{ required: true, message: t('Please enter rule name') }]}
          >
            <Input placeholder={t('e.g., Sales Spike Alert')} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            name="metric"
            label={t('Metric')}
            rules={[{ required: true, message: t('Please enter metric name') }]}
            tooltip={t('Name of the metric column to monitor (e.g., sales, count, sum_amount)')}
          >
            <Input placeholder={t('e.g., sales, count')} />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item name="description" label={t('Description (Optional)')}>
        <TextArea rows={2} placeholder={t('Enter description for this rule')} />
      </Form.Item>

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            name="rule_type"
            label={t('Detection Type')}
            rules={[{ required: true, message: t('Please select detection type') }]}
          >
            <Select>
              {RULE_TYPE_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>
                  {opt.label}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item name="status" label={t('Status')}>
            <Select>
              <Option value="active">{t('Active')}</Option>
              <Option value="inactive">{t('Inactive')}</Option>
            </Select>
          </Form.Item>
        </Col>
      </Row>

      <Divider>{t('Rule Configuration')}</Divider>

      {renderRuleConfigFields()}

      <Form.Item style={{ marginTop: '24px', textAlign: 'right' }}>
        <Space>
          <Button onClick={onCancel}>{t('Cancel')}</Button>
          <Button type="primary" htmlType="submit" loading={loading}>
            {editingRule ? t('Update Rule') : t('Create Rule')}
          </Button>
        </Space>
      </Form.Item>
    </Form>
  );
};

export const AnomalyRuleConfig: FC<AnomalyRuleConfigProps> = ({
  chartId,
  dashboardId,
  visible,
  onClose,
  anomalyDetection,
}) => {
  const [loading, setLoading] = useState(false);
  const [existingRules, setExistingRules] = useState<AnomalyRule[]>([]);
  const [editingRule, setEditingRule] = useState<AnomalyRule | null>(null);
  const [activeTab, setActiveTab] = useState<'list' | 'form'>('list');

  const currentUserId = useSelector<RootState, number>(
    state => (state as any).common?.current_user?.userId ?? 1,
  );

  const fetchExistingRules = useCallback(async () => {
    try {
      const response = await getAnomalyRules(chartId);
      setExistingRules(response.result);
    } catch (error) {
      console.error('Failed to fetch anomaly rules:', error);
      message.error(t('Failed to load anomaly rules'));
    }
  }, [chartId]);

  useEffect(() => {
    if (visible) {
      fetchExistingRules();
    }
  }, [visible, fetchExistingRules]);

  const handleEdit = useCallback((rule: AnomalyRule) => {
    setEditingRule(rule);
    setActiveTab('form');
  }, []);

  const handleCancel = useCallback(() => {
    setEditingRule(null);
    setActiveTab('list');
  }, []);

  const handleDelete = useCallback(
    async (id: number) => {
      try {
        await deleteAnomalyRule(id);
        message.success(t('Anomaly rule deleted successfully'));
        fetchExistingRules();
      } catch (error) {
        console.error('Failed to delete anomaly rule:', error);
        message.error(t('Failed to delete anomaly rule'));
      }
    },
    [fetchExistingRules],
  );

  const handleSubmit = useCallback(
    async (values: Record<string, unknown>) => {
      setLoading(true);
      try {
        let ruleConfig: Record<string, unknown> = {};

        switch (values.rule_type) {
          case 'threshold':
            ruleConfig = {
              threshold_min: values.threshold_min as number | undefined,
              threshold_max: values.threshold_max as number | undefined,
            };
            break;
          case 'mom':
          case 'yoy':
            ruleConfig = {
              change_percent: values.change_percent as number,
              change_absolute: values.change_absolute as number | undefined,
              direction: values.direction as AnomalyDirection,
            };
            break;
          case 'period_over_period':
            ruleConfig = {
              change_percent: values.change_percent as number,
              change_absolute: values.change_absolute as number | undefined,
              direction: values.direction as AnomalyDirection,
              period_offset: values.period_offset as number,
            };
            break;
          case 'consecutive':
            ruleConfig = {
              consecutive_count: values.consecutive_count as number,
              direction: values.direction as AnomalyDirection,
            };
            break;
        }

        const ruleData: AnomalyRuleRequest = {
          name: values.name as string,
          description: values.description as string | undefined,
          chart_id: chartId,
          dashboard_id: dashboardId,
          metric: values.metric as string,
          rule_type: values.rule_type as AnomalyRuleType,
          rule_config: ruleConfig as unknown as AnomalyRuleRequest['rule_config'],
          status: values.status as AnomalyRuleStatus,
          owners: [currentUserId],
        };

        if (editingRule) {
          await updateAnomalyRule(editingRule.id, ruleData);
          message.success(t('Anomaly rule updated successfully'));
        } else {
          await createAnomalyRule(ruleData);
          message.success(t('Anomaly rule created successfully'));
        }

        setEditingRule(null);
        setActiveTab('list');
        fetchExistingRules();
      } catch (error) {
        console.error('Failed to save anomaly rule:', error);
        message.error(t('Failed to save anomaly rule'));
      } finally {
        setLoading(false);
      }
    },
    [chartId, dashboardId, currentUserId, editingRule, fetchExistingRules],
  );

  const modalTitle = useMemo(
    () => (
      <Space>
        <Title level={4} style={{ margin: 0 }}>
          {t('Anomaly Detection Rules')}
        </Title>
        <Tag color={anomalyDetection?.has_anomalies ? 'error' : 'success'}>
          {anomalyDetection?.has_anomalies
            ? t('Has Anomalies')
            : anomalyDetection?.has_anomaly_rules
            ? t('Monitoring')
            : t('No Rules')}
        </Tag>
      </Space>
    ),
    [anomalyDetection],
  );

  const tabItems = [
    {
      key: 'list',
      label: t('Existing Rules'),
      children: (
        <>
          <AnomalyRuleList
            rules={existingRules}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
          <div style={{ marginTop: '16px', textAlign: 'center' }}>
            <Button
              type="primary"
              icon={<i className="fa fa-plus" />}
              onClick={() => {
                setEditingRule(null);
                setActiveTab('form');
              }}
            >
              {t('Create New Rule')}
            </Button>
          </div>
        </>
      ),
    },
    {
      key: 'form',
      label: editingRule ? t('Edit Rule') : t('Create Rule'),
      children: (
        <AnomalyRuleForm
          chartId={chartId}
          dashboardId={dashboardId}
          editingRule={editingRule}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          loading={loading}
        />
      ),
    },
  ];

  return (
    <Modal
      title={modalTitle}
      open={visible}
      onCancel={onClose}
      footer={null}
      width={800}
    >
      <Tabs
        activeKey={activeTab}
        onChange={key => setActiveTab(key as 'list' | 'form')}
        items={tabItems}
      />
    </Modal>
  );
};

export default AnomalyRuleConfig;
