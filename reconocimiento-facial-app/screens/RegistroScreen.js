import React, { useState } from 'react';
import { View, Text, TextInput, Button, Alert, Switch, StyleSheet, ScrollView } from 'react-native';
import { registrarUsuario } from '../services/api';

const RegistroScreen = ({ navigation }) => {
  const [nombre, setNombre] = useState('');
  const [apellido, setApellido] = useState('');
  const [codigoUnico, setCodigoUnico] = useState('');
  const [email, setEmail] = useState('');
  const [requisitoriado, setRequisitoriado] = useState(false);
  const [subiendo, setSubiendo] = useState(false);

  const registrar = async () => {
    // Validación de campos vacíos
    if (!nombre || !apellido || !codigoUnico || !email) {
      Alert.alert('Campos obligatorios', 'Por favor completa todos los campos.');
      return;
    }

    // Validación de correo
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      Alert.alert('Email inválido', 'Por favor ingresa un email válido.');
      return;
    }

    // Log de los datos antes de enviarlos
    console.log({
      nombre, apellido, codigoUnico, email, requisitoriado
    });

    try {
      setSubiendo(true);

      const formData = new FormData();
      formData.append('nombre', nombre);
      formData.append('apellido', apellido);
      formData.append('codigo_unico', codigoUnico);  // Asegurarse de que el nombre coincide
      formData.append('email', email);
      formData.append('requisitoriado', requisitoriado ? '1' : '0');  // Convertir booleano a '1' o '0'

      const respuesta = await registrarUsuario(formData);

      if (!respuesta || !respuesta.id_usuario) {
        throw new Error('No se recibió ID de usuario del servidor');
      }

      const idUsuario = respuesta.id_usuario;
      Alert.alert('Éxito', `Usuario registrado correctamente. Tu ID es: ${idUsuario}`);
      navigation.navigate('Home');
    } catch (error) {
      console.error('Error en registro:', error);
      Alert.alert(
        'Error', 
        error.message || 'No se pudo registrar el usuario. Verifica tu conexión e intenta nuevamente.'
      );
    } finally {
      setSubiendo(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.titulo}>Registro de Usuario</Text>

      <TextInput 
        style={styles.input} 
        placeholder="Nombre" 
        value={nombre} 
        onChangeText={setNombre} 
      />
      <TextInput 
        style={styles.input} 
        placeholder="Apellido" 
        value={apellido} 
        onChangeText={setApellido} 
      />
      <TextInput 
        style={styles.input} 
        placeholder="Código Único" 
        value={codigoUnico} 
        onChangeText={setCodigoUnico}
        maxLength={20}
      />
      <TextInput 
        style={styles.input} 
        placeholder="Correo Electrónico" 
        value={email} 
        onChangeText={setEmail} 
        keyboardType="email-address"
        autoCapitalize="none"
      />

      <View style={styles.switchContainer}>
        <Text>¿Requisitoriado?</Text>
        <Switch 
          value={requisitoriado} 
          onValueChange={setRequisitoriado} 
          trackColor={{ false: "#767577", true: "#ff0000" }}
          thumbColor={requisitoriado ? "#f4f3f4" : "#f4f3f4"}
        />
      </View>

      <Button 
        title={subiendo ? 'Registrando...' : 'Registrar Usuario'} 
        onPress={registrar} 
        disabled={subiendo} 
        color="#4CAF50"
      />
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { 
    padding: 20,
    paddingBottom: 40 
  },
  titulo: { 
    fontSize: 22, 
    fontWeight: 'bold', 
    marginBottom: 20, 
    textAlign: 'center',
    color: '#333'
  },
  input: { 
    borderWidth: 1, 
    borderColor: '#ccc', 
    borderRadius: 8, 
    padding: 12, 
    marginBottom: 15,
    fontSize: 16
  },
  switchContainer: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    justifyContent: 'space-between', 
    marginBottom: 15,
    paddingHorizontal: 5
  },
});

export default RegistroScreen;


