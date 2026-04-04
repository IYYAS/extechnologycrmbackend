from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from .models import Project, Group, Tag

class ProjectTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.project_data = {'name': 'Project Alpha', 'price': '100.00'}
        self.response = self.client.post(
            reverse('project-list-create'),
            self.project_data,
            format='json'
        )

    def test_create_project(self):
        self.assertEqual(self.response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(Project.objects.get().name, 'Project Alpha')

    def test_get_project(self):
        project = Project.objects.get()
        response = self.client.get(
            reverse('project-detail', kwargs={'pk': project.id}),
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], project.name)

    def test_update_project(self):
        project = Project.objects.get()
        updated_data = {'name': 'Project Beta', 'price': '200.00'}
        response = self.client.put(
            reverse('project-detail', kwargs={'pk': project.id}),
            updated_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        project.refresh_from_db()
        self.assertEqual(project.name, 'Project Beta')
        self.assertEqual(project.price, 200.00)

    def test_delete_project(self):
        project = Project.objects.get()
        response = self.client.delete(
            reverse('project-detail', kwargs={'pk': project.id}),
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Project.objects.count(), 0)

class GroupTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.project = Project.objects.create(name='Project Gamma', price='300.00')
        self.group_data = {'name1': 'Group A', 'name2': 'Group B', 'project': self.project.id}
        self.response = self.client.post(
            reverse('group-list-create'),
            self.group_data,
            format='json'
        )

    def test_create_group(self):
        self.assertEqual(self.response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Group.objects.count(), 1)
        self.assertEqual(Group.objects.get().name1, 'Group A')

    def test_update_group(self):
        group = Group.objects.get()
        updated_data = {'name1': 'Group C', 'name2': 'Group D', 'project': self.project.id}
        response = self.client.put(
            reverse('group-detail', kwargs={'pk': group.id}),
            updated_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        group.refresh_from_db()
        self.assertEqual(group.name1, 'Group C')

    def test_delete_group(self):
        group = Group.objects.get()
        response = self.client.delete(
            reverse('group-detail', kwargs={'pk': group.id}),
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Group.objects.count(), 0)

class TagTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tag_data = {'name': 'Tag A'}
        self.response = self.client.post(
            reverse('tag-list-create'),
            self.tag_data,
            format='json'
        )

    def test_create_tag(self):
        self.assertEqual(self.response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Tag.objects.count(), 1)
        self.assertEqual(Tag.objects.get().name, 'Tag A')

    def test_update_tag(self):
        tag = Tag.objects.get()
        updated_data = {'name': 'Tag B'}
        response = self.client.put(
            reverse('tag-detail', kwargs={'pk': tag.id}),
            updated_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, 'Tag B')

    def test_delete_tag(self):
        tag = Tag.objects.get()
        response = self.client.delete(
            reverse('tag-detail', kwargs={'pk': tag.id}),
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Tag.objects.count(), 0)
