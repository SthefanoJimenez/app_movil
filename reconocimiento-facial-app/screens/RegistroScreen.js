import React, { useState } from 'react';
import { View, Text, TextInput, Button, Image, StyleSheet, Alert, Switch, ScrollView } from 'react-native';
import { registrarUsuario } from '../services/api';

const RegistroScreen = ({ route, navigation }) => {
  const { imagen } = route.params;

  const [nombre, setNombre] = useState('');
  const [apellido, setApellido] = useState('');
  const [codigoUnico, setCodigoUnico] = useState('');
  const [email, setEmail] = useState('');
  const [requisitoriado, setRequisitoriado] = useState(false);
  const [enviando, setEnviando] = useState(false);

  const handleRegistro = async () => {
    if (!nombre || !apellido || !codigoUnico || !email) {
      Alert.alert('Campos incompletos', 'Por favor, llena todos los campos.');
      return;
    }

    setEnviando(true);

    try {
      const res = await registrarUsuario({
        nombre,
        apellido,
        codigoUnico,
        email,
        requisitoriado,
        imagen,
      });

      Alert.alert('Éxito', 'Usuario registrado correctamente');
      navigation.goBack(); // Volver a la pantalla anterior
    } catch (err) {
      console.log('Error al registrar:', err);
      Alert.alert('Error', 'No se pudo registrar el usuario.');
    } finally {
      setEnviando(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Registro de Nuevo Usuario</Text>

      <Image source={{ uri: imagen.uri }} style={styles.imagen} />

      <TextInput placeholder="Nombre" style={styles.input} value={nombre} onChangeText={setNombre} />
      <TextInput placeholder="Apellido" style={styles.input} value={apellido} onChangeText={setApellido} />
      <TextInput placeholder="Código Único" style={styles.input} value={codigoUnico} onChangeText={setCodigoUnico} />
      <TextInput placeholder="Email" style={styles.input} value={email} onChangeText={setEmail} keyboardType="email-address" />

      <View style={styles.switchContainer}>
        <Text>¿Está requisitoriado?</Text>
        <Switch value={requisitoriado} onValueChange={setRequisitoriado} />
      </View>

      <Button title={enviando ? "Registrando..." : "Registrar Usuario"} onPress={handleRegistro} disabled={enviando} />
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 20,
    alignItems: 'center',
  },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 20 },
  imagen: { width: 200, height: 200, marginBottom: 20, borderRadius: 10 },
  input: {
    width: '100%',
    padding: 10,
    marginVertical: 8,
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
  },
  switchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 12,
    gap: 10,
  },
});

export default RegistroScreen;
