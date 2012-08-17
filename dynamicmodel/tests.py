"""
Tests for DynamicModel, DynamicModelWithSchema and DynamicForm
"""

from django.test import TestCase
from .models import DynamicModel, DynamicForm, DynamicSchemaField
from django.db import models


class TestModel(DynamicModel):

    TYPE = (
        ('email', 'Email item'),
        ('contact', 'Contact item'),
    )

    type = models.CharField(max_length=100, choices=TYPE, editable=False)
    about = models.CharField(max_length=100, default='about value')

    @classmethod
    def get_schema_type_descriptor(cls):
        return 'type'


class TestForm(DynamicForm):

    class Meta:
        model = TestModel


class FalseModel(models.Model):

    TYPE = (
        ('email', 'Email item'),
        ('contact', 'Contact item'),
    )

    type = models.CharField(max_length=100, choices=TYPE, editable=False)
    about = models.CharField(max_length=100, default='about value')

    @classmethod
    def get_schema_type_descriptor(cls):
        return 'type'


class FalseForm(DynamicForm):

    class Meta:
        model = FalseModel


class TypelessModel(DynamicModel):

    about = models.CharField(max_length=100, default='about value')


class TypelessForm(DynamicForm):

    class Meta:
        model = TypelessModel


# testing DynamicModel
class DynamicModelTest(TestCase):

    def setUp(self):

        DynamicSchemaField.objects.all().delete()

    def test_extra_fields_db_save(self):

        model = TestModel()
        DynamicSchemaField.objects.create(schema=model.get_schema(),
            name='experiment', field_type='CharField')

        self.ex_val = "experimental value"
        model.experiment = self.ex_val
        model.save()
        model_db_id = model.id

        new_model = TestModel.objects.get(pk=model_db_id)
        self.assertEqual(self.ex_val, new_model.experiment)

    def test_get_nonexistent_attr(self):

        model = TestModel()
        self.assertRaises(AttributeError, getattr, model, "attribute_that_does_not_exist")

    def test_dyn_attr_in_extra_fields(self):

        model = TestModel()
        DynamicSchemaField.objects.create(schema=model.get_schema(),
            name='experiment', field_type='CharField')

        self.ex_val = "experimental value"
        model.experiment = self.ex_val
        model.save()
        model_db_id = model.id

        new_model = TestModel.objects.get(pk=model_db_id)
        self.assertEqual(new_model.extra_fields['experiment'],
            new_model.experiment)

    def test_dyn_attr_changes_extra_fields(self):

        model = TestModel()
        DynamicSchemaField.objects.create(schema=model.get_schema(), name='experiment2',
            field_type='CharField')

        model.experiment2 = "experiment2 value"
        self.assertEqual(model.extra_fields['experiment2'],
            model.experiment2)

    def test_accept_schema_attr(self):

        model = TestModel()
        DynamicSchemaField.objects.create(schema=model.get_schema(), name='schema',
            field_type='CharField')

        model.schema = "schema value changed"
        self.assertEqual(model.extra_fields['schema'], model.schema)

    def test_underscore_schema_attr_fail(self):

        model = TestModel()
        # this dyn field has no effect because _schema is reserved attr
        DynamicSchemaField.objects.create(schema=model.get_schema(), name='_schema',
            field_type='CharField')

        model._schema = "schema value changed"
        self.assertNotEqual(model.get_extra_field_value('_schema'), model._schema)

    def test_extend_ignore_attrs(self):

        model = TestModel()

        model.schema = "schema value"
        self.assertNotIn('schema', model.extra_fields)

        model.schema_custom_ignore = "schema_custom_ignore value"
        self.assertNotIn('schema_custom_ignore', model.extra_fields)

        self.assertTrue(hasattr(model, '_meta'))
        model._meta = model._meta
        self.assertNotIn('_meta', model.extra_fields)

        model.about = "about text"
        self.assertNotIn('about', model.extra_fields)


# testing DynamicModel and DynamicForm
class DynamicFormTest(TestCase):

    def setUp(self):
        """prepare DynamicFormTest environment"""

        DynamicSchemaField.objects.all().delete()

    def test_accept_any_extra_field(self):

        model = TestModel()
        DynamicSchemaField.objects.create(schema=model.get_schema(), name='email',
            field_type='EmailField')

        form = TestForm({
            'about': 'about change',
            'fail_field': 'fail field',
            'email': 'a@a.com',
        }, instance=model)

        form.is_valid()
        self.assertFalse(form['about'].errors)
        self.assertFalse(form['email'].errors)

    def test_validate_schema_fields(self):

        model = TestModel()
        DynamicSchemaField.objects.create(schema=model.get_schema(), name='email',
            field_type='EmailField')

        # should fail with invalid email value
        form_invalid = TestForm({
            'about': 'about change',
            'email': 'wrong email',
        }, instance=model)

        form_invalid.is_valid()
        self.assertFalse(form_invalid['about'].errors)
        self.assertTrue(form_invalid['email'].errors)

        # should pass with valid email value
        form = TestForm({
            'about': 'about change',
            'email': 'a@a.com',
        }, instance=model)

        form.is_valid()
        self.assertFalse(form['about'].errors)
        self.assertFalse(form['email'].errors)

    def test_validate_schema_fields_typeless(self):
        """Test form validation on dynamicmodel that has no
        get_schema_type_descriptor method declared
        """
        model = TypelessModel()
        DynamicSchemaField.objects.create(schema=model.get_schema(), name='email',
            field_type='EmailField')

        # should fail with invalid email value
        form_invalid = TypelessForm({
            'about': 'about change',
            'email': 'wrong email',
        }, instance=model)

        form_invalid.is_valid()
        self.assertFalse(form_invalid['about'].errors)
        self.assertTrue(form_invalid['email'].errors)

        # should pass with valid email value
        form = TypelessForm({
            'about': 'about change',
            'email': 'a@a.com',
        }, instance=model)

        form.is_valid()
        self.assertFalse(form['about'].errors)
        self.assertFalse(form['email'].errors)

    def test_form_with_type(self):

        # init schema fields
        info_model = TestModel(type='info')
        DynamicSchemaField.objects.create(schema=info_model.get_schema(), name='info',
            field_type='TextField')
        DynamicSchemaField.objects.create(schema=info_model.get_schema(), name='more_info',
            field_type='TextField', required=False)

        # should pass with info value set and
        # more_info empty (more_info not required)
        info_form = TestForm({
            'about': 'about change',
            'info': 'some info text',
            'more_info': '',
        }, instance=info_model)

        self.assertTrue(info_form.is_valid())

    def test_form_create(self):

        model = TestModel()
        DynamicSchemaField.objects.create(schema=model.get_schema(), name='email',
            field_type='EmailField')

        form = TestForm({
            'about': 'about change',
            'email': 'a@a.com',
        }, model)

        model_from_form = form.save()

        model_from_db = TestModel.objects.get(pk=model_from_form.id)

        self.assertEqual(model_from_form.get_field_dict(),
            model_from_db.get_field_dict())

    def test_false_form(self):

        self.assertRaises(ValueError, FalseForm)